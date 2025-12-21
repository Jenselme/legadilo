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
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms import BaseInlineTableFormSet
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.forms.widgets import SelectAutocompleteWidget
from legadilo.core.utils.urls import add_query_params, pop_query_param, validate_referer_url
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticlesGroup, Tag
from legadilo.reading.models.article import SaveArticleResult
from legadilo.reading.models.articles_group import ArticlesGroupQuerySet
from legadilo.reading.services.article_fetching import (
    fetch_article_data,
)
from legadilo.reading.services.articles_groups import SaveArticlesGroupResult, save_articles_group
from legadilo.users.user_types import AuthenticatedHttpRequest


class FetchArticleForm(forms.Form):
    url = forms.URLField(
        max_length=2048,
        assume_scheme="https",
        help_text=_("URL of the article to add."),
    )
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this article. To create a new tag, type and press enter."
        ),
    )
    group = forms.ModelChoiceField(
        ArticlesGroup.objects.none(),
        required=False,
        widget=SelectAutocompleteWidget(allow_new=False),
        help_text=_(
            "Group to add the article to. If you need to create a new group, use the form below."
        ),
    )

    class Meta:
        fields = ("url", "tags")

    def __init__(
        self,
        *args,
        tag_choices: list[tuple[str, str]],
        groups_qs: ArticlesGroupQuerySet,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["group"].queryset = groups_qs  # type: ignore[attr-defined]
        self.fields["group"].label_from_instance = lambda obj: obj.title  # type: ignore[attr-defined]


class ArticleGroupForm(forms.Form):
    title = forms.CharField(
        max_length=constants.ARTICLES_GROUP_MAX_LENGTH,
        help_text=_("Title of the group."),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
            }
        ),
        help_text=_("Description of the group."),
    )
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this group and all articles in it. "
            "To create a new tag, type and press enter."
        ),
    )

    class Meta:
        fields = ("title", "description", "tags")

    def __init__(self, *args, tag_choices: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]


class ArticleGroupLinkForm(forms.Form):
    url = forms.URLField(
        required=True,
        max_length=2048,
        assume_scheme="https",
        help_text=_("URL of an article to add to the group."),
    )


@require_http_methods(["GET", "POST"])
@login_required
def add_article_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    tag_choices, hierarchy = Tag.objects.get_all_choices_with_hierarchy(request.user)
    add_article_form = FetchArticleForm(
        tag_choices=tag_choices,
        groups_qs=ArticlesGroup.objects.get_queryset().for_user(request.user),
    )
    add_article_result = None
    articles_group_form = ArticleGroupForm(tag_choices=tag_choices)
    article_group_link_formset = _build_article_group_link_formset()
    save_articles_group_result = None
    status = HTTPStatus.OK

    if request.method == "POST" and "add_article" in request.POST:
        status, add_article_form, add_article_result = _handle_article_save(
            request, tag_choices, force_update=False
        )
    elif request.method == "POST":
        status, articles_group_form, article_group_link_formset, save_articles_group_result = (
            _handle_articles_group_save(request, tag_choices)
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
            "tags_hierarchy": hierarchy,
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
    request: AuthenticatedHttpRequest, tag_choices: list[tuple[str, str]]
) -> tuple[
    HTTPStatus,
    ArticleGroupForm,
    BaseInlineTableFormSet[ArticleGroupLinkForm],
    SaveArticlesGroupResult | None,
]:
    articles_group_form = ArticleGroupForm(data=request.POST, tag_choices=tag_choices)
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
        ArticleGroupForm(tag_choices=tag_choices),
        _build_article_group_link_formset(),
        save_result,
    )


@require_http_methods(["POST"])
@login_required
def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    article = get_object_or_404(Article, url=request.POST.get("url"), user=request.user)
    _status, _form, save_result = _handle_article_save(
        request,
        [],
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
    request: AuthenticatedHttpRequest,
    tag_choices: list[tuple[str, str]],
    *,
    force_update: bool,
) -> tuple[HTTPStatus, FetchArticleForm, SaveArticleResult | None]:
    form = FetchArticleForm(
        request.POST,
        tag_choices=tag_choices,
        groups_qs=ArticlesGroup.objects.get_queryset().for_user(request.user),
    )
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    article_url = form.cleaned_data["url"]
    fetch_article_result = fetch_article_data(article_url)
    with transaction.atomic():
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
        save_result = Article.objects.save_from_fetch_results(
            request.user, [fetch_article_result], tags, force_update=force_update
        )[0]
        # Group cannot be removed from here: we are either creating a new article of refetching the
        # content of an existing article. Link between articles and groups are handled on article
        # details.
        if save_result.was_created and (group := form.cleaned_data.get("group")):
            Article.objects.link_articles_to_group(group, [save_result.article])

    new_tags = Tag.objects.get_all_choices(request.user)
    if save_result.was_created:
        # Refresh tags to get the newly created ones.
        return (
            HTTPStatus.CREATED,
            FetchArticleForm(
                tag_choices=new_tags,
                groups_qs=ArticlesGroup.objects.get_queryset().for_user(request.user),
            ),
            save_result,
        )

    return (
        HTTPStatus.OK,
        FetchArticleForm(
            tag_choices=new_tags,
            groups_qs=ArticlesGroup.objects.get_queryset().for_user(request.user),
        ),
        save_result,
    )
