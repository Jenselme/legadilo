# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms import BaseInlineTableFormSet
from legadilo.core.forms.fields import MultipleTagsField, SlugifiableAutocompleteField
from legadilo.core.forms.widgets import SelectAutocompleteWidget
from legadilo.core.utils.security import sanitize_keep_safe_tags
from legadilo.core.utils.urls import add_query_params, pop_query_param, validate_referer_url
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticlesGroup, Tag
from legadilo.reading.models.article import SaveArticleResult
from legadilo.reading.services.article_fetching import (
    fetch_article_data,
)
from legadilo.reading.services.articles_groups import SaveArticlesGroupResult, save_articles_group
from legadilo.users.user_types import AuthenticatedHttpRequest


class FetchArticleForm(forms.Form):
    url = forms.URLField(
        label=_("Article URL"),
        max_length=2048,
        assume_scheme="https",
        help_text=_("URL of the article to add."),
    )
    tags = MultipleTagsField(
        label=_("Tags"),
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this article. To create a new tag, type and press enter."
        ),
    )
    group = SlugifiableAutocompleteField(
        label=_("Group"),
        required=False,
        widget=SelectAutocompleteWidget(
            empty_label=_("Choose the group"),
            allow_new=True,
            server_url=reverse_lazy("reading:articles_groups_autocomplete"),
        ),
        help_text=_(
            "Group to add the article to. If you need to create a new group, type and press enter."
        ),
    )

    class Meta:
        fields = ("url", "tags")


class ArticleGroupForm(forms.Form):
    title = forms.CharField(
        label=_("Group title"),
        required=True,
        max_length=constants.ARTICLES_GROUP_TITLE_MAX_LENGTH,
        help_text=_("Title of the group."),
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
            }
        ),
        help_text=_("Description of the group."),
    )
    tags = MultipleTagsField(
        label=_("Tags"),
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this group and all articles in it. "
            "To create a new tag, type and press enter."
        ),
    )

    class Meta:
        fields = ("title", "description", "tags")

    def clean_description(self):
        return sanitize_keep_safe_tags(self.cleaned_data["description"])


class ArticleGroupLinkForm(forms.Form):
    url = forms.URLField(
        label=_("Articles URLs"),
        required=True,
        max_length=2048,
        assume_scheme="https",
        help_text=_("URL of an article to add to the group."),
    )


@require_http_methods(["GET", "POST"])
@login_required
def add_article_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    add_article_form = FetchArticleForm()
    add_article_result = None
    articles_group_form = ArticleGroupForm()
    article_group_link_formset = _build_article_group_link_formset()
    save_articles_group_result = None
    status = HTTPStatus.OK

    if request.method == "POST" and "add_article" in request.POST:
        status, add_article_form, add_article_result = _handle_article_save(
            request, force_update=False
        )
    elif request.method == "POST":
        status, articles_group_form, article_group_link_formset, save_articles_group_result = (
            _handle_articles_group_save(request)
        )

    return TemplateResponse(
        request,
        "reading/add_article.html",
        {
            "add_article_form": add_article_form,
            "add_article_result": add_article_result,
            "max_article_size": constants.MAX_ARTICLE_FILE_SIZE / (1024 * 1024),
            "articles_group_form": articles_group_form,
            "article_group_link_formset": article_group_link_formset,
            "save_articles_group_result": save_articles_group_result,
        },
        status=status,
    )


def _build_article_group_link_formset(data=None):
    return formset_factory(
        ArticleGroupLinkForm,
        formset=BaseInlineTableFormSet,
        min_num=1,
        extra=1,
    )(data)


def _handle_articles_group_save(
    request: AuthenticatedHttpRequest,
) -> tuple[
    HTTPStatus,
    ArticleGroupForm,
    BaseInlineTableFormSet[ArticleGroupLinkForm],
    SaveArticlesGroupResult | None,
]:
    articles_group_form = ArticleGroupForm(data=request.POST)
    article_group_link_formset = _build_article_group_link_formset(request.POST)

    if not articles_group_form.is_valid() or not article_group_link_formset.is_valid():
        return HTTPStatus.BAD_REQUEST, articles_group_form, article_group_link_formset, None

    urls = [data["url"] for data in article_group_link_formset.cleaned_data if data.get("url")]
    save_result = save_articles_group(
        request.user,
        articles_group_form.cleaned_data["title"],
        articles_group_form.cleaned_data["description"],
        articles_group_form.cleaned_data["tags"],
        urls,
    )
    return (
        HTTPStatus.CREATED,
        ArticleGroupForm(),
        _build_article_group_link_formset(),
        save_result,
    )


@require_http_methods(["POST"])
@login_required
def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    article = get_object_or_404(Article, url=request.POST.get("url"), user=request.user)
    _status, _form, save_result = _handle_article_save(
        request,
        force_update=True,
    )
    _handle_refetch_article_save_result(request, save_result)

    article.refresh_from_db()
    _url, from_url = pop_query_param(
        validate_referer_url(request, reverse("reading:default_reading_list")), "from_url"
    )
    new_article_url = add_query_params(
        reverse(
            "reading:article_details",
            kwargs={"article_id": article.id, "article_slug": article.slug},
        ),
        {"from_url": from_url},
    )

    return HttpResponseRedirect(new_article_url)


def _handle_refetch_article_save_result(
    request: AuthenticatedHttpRequest, save_result: SaveArticleResult | None
):
    if not save_result:
        return

    if save_result.article.content:
        messages.success(request, _("The article was successfully re-fetched!"))
        return

    messages.warning(
        request,
        _(
            "The article was re-fetched but its content couldn't be fetched. "
            "Please check that it really points to an article."
        ),
    )


def _handle_article_save(
    request: AuthenticatedHttpRequest, *, force_update: bool
) -> tuple[HTTPStatus, FetchArticleForm, SaveArticleResult | None]:
    form = FetchArticleForm(request.POST)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    article_url = form.cleaned_data["url"]
    fetch_article_result = fetch_article_data(article_url)
    with transaction.atomic():
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
        save_result = Article.objects.save_from_fetch_results(
            request.user, [fetch_article_result], tags, force_update=force_update
        )[0]
        # Groups can only be linked to articles that have been created. For existing articles, user
        # must change the group on the article details page.
        if save_result.was_created and (group_slug := form.cleaned_data.get("group")):
            group = ArticlesGroup.objects.get_or_create_from_slug(request.user, group_slug)
            Article.objects.link_articles_to_group(group, [save_result.article])

    if save_result.was_created:
        # Refresh linked models to get the newly created ones.
        return (
            HTTPStatus.CREATED,
            FetchArticleForm(),
            save_result,
        )

    return (
        HTTPStatus.OK,
        FetchArticleForm(),
        save_result,
    )
