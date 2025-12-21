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
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csp import csp_override
from django.views.decorators.http import require_http_methods

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.utils.types import FormChoices
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticlesGroup, ArticleTag, Tag
from legadilo.users.user_types import AuthenticatedHttpRequest

from ...core.forms.widgets import SelectAutocompleteWidget
from ..models.articles_group import ArticlesGroupQuerySet
from ._utils import get_from_url_for_article_details
from .comment_views import CommentArticleForm


class EditArticleForm(forms.Form):
    title = forms.CharField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH, required=True)
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
            "Group to associate this article with. If you need to create a new group, create it "
            "from the groups list page."
        ),
    )
    reading_time = forms.IntegerField(required=True, min_value=0)

    class Meta:
        fields = ("tags", "title", "reading_time")

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
        ArticleTag.objects.associate_articles_with_tags([article], tags)
        ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)
        article.update_from_details(**form.cleaned_data)
        article.save()
        # Update the list of tag choices. We may have created some new one.
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
            "reading_time": article.reading_time,
            "group": article.group_id,
        },
        tag_choices=tag_choices,
        groups_qs=ArticlesGroup.objects.get_queryset().for_user(article.user),
    )
