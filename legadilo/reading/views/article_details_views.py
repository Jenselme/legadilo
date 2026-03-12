# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csp import csp_override
from django.views.decorators.http import require_http_methods

from legadilo.core.forms.fields import MultipleTagsField, SlugifiableAutocompleteField
from legadilo.core.utils.types import FormChoices
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, Tag
from legadilo.users.user_types import AuthenticatedHttpRequest

from ...core.forms.widgets import SelectAutocompleteWidget
from ...core.utils.security import sanitize_keep_safe_tags
from ..services.articles_groups import update_article_group
from ._utils import get_from_url_for_article_details
from .comment_views import CommentArticleForm


class EditArticleForm(forms.Form):
    title = forms.CharField(
        label=_("Title"), max_length=constants.ARTICLE_TITLE_MAX_LENGTH, required=True
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
    reading_time = forms.IntegerField(required=True, min_value=0)
    summary = forms.CharField(
        label=_("Summary"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text=_("Safe HTML tags are allowed. All other HTML tags will be removed."),
    )

    class Meta:
        fields = ("tags", "title", "reading_time", "summary", "group")

    def __init__(
        self, *args, tag_choices: FormChoices, group_choices: FormChoices | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]
        if group_choices:
            self.fields["group"].choices = group_choices  # type: ignore[attr-defined]

    def clean_summary(self):
        return sanitize_keep_safe_tags(self.cleaned_data["summary"])


@require_http_methods(["GET", "POST"])
@login_required
@csp_override({"img-src": settings.SECURE_CSP["img-src"] + ("https:",)})
def article_details_view(
    request: AuthenticatedHttpRequest, article_id: int, article_slug: str
) -> TemplateResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(),
        id=article_id,
        slug=article_slug,
        user=request.user,
    )
    tag_choices, hierarchy = Tag.objects.get_all_choices_with_hierarchy(request.user)
    if request.method == "POST":
        status, edit_article_form, article = _handle_update(request, article, tag_choices)
    else:
        status = HTTPStatus.OK
        edit_article_form = _build_edit_article_form_from_instance(tag_choices, article)

    return TemplateResponse(
        request,
        "reading/article_details.html",
        {
            "base": {
                "author": ", ".join(article.authors),
                "fluid_content": True,
            },
            "article": article,
            "edit_article_form": edit_article_form,
            "comment_article_form": CommentArticleForm(),
            "from_url": get_from_url_for_article_details(request, request.GET),
            "tags_hierarchy": hierarchy,
        },
        status=status,
    )


@transaction.atomic()
def _handle_update(
    request: AuthenticatedHttpRequest, article: Article, tag_choices: FormChoices
) -> tuple[HTTPStatus, EditArticleForm, Article]:
    form = _build_edit_article_form_from_instance(tag_choices, article, request.POST)
    status = HTTPStatus.BAD_REQUEST
    if form.is_valid():
        status = HTTPStatus.OK
        tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data.pop("tags"))
        group_slug = form.cleaned_data.pop("group")
        update_article_group(article, group_slug)
        ArticleTag.objects.associate_articles_with_tags([article], tags)
        ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)
        article.update_from_details(**form.cleaned_data)
        article.save()
        # Update the list of linked models. We may have created some new one.
        tag_choices = Tag.objects.get_all_choices(request.user)
        form = _build_edit_article_form_from_instance(tag_choices, article)

    # Refresh the many-to-many relationship of tags to display the latest value.
    return status, form, Article.objects.get_queryset().for_details().get(id=article.id)


def _build_edit_article_form_from_instance(tag_choices: FormChoices, article: Article, data=None):
    return EditArticleForm(
        data=data,
        initial={
            "tags": article.article_tags.get_selected_values(),
            "title": article.title,
            "summary": article.summary,
            "reading_time": article.reading_time,
            "group": article.group.slug if article.group else None,
        },
        tag_choices=tag_choices,
        group_choices=[(article.group.slug, article.group.title)] if article.group else [],
    )
