# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from http import HTTPStatus

from csp.decorators import csp_update
from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms import FormChoices
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, Tag
from legadilo.reading.services.views import get_from_url_for_article_details
from legadilo.users.user_types import AuthenticatedHttpRequest


class EditArticleForm(forms.Form):
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this article. To create a new tag, type and press enter."
        ),
    )
    title = forms.CharField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH, required=True)
    reading_time = forms.IntegerField(required=True, min_value=0)

    class Meta:
        fields = ("tags", "title", "reading_time")

    def __init__(
        self,
        *args,
        tag_choices: list[tuple[str, str]],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]


@require_http_methods(["GET", "POST"])
@login_required
@csp_update(IMG_SRC="https:")
def article_details_view(
    request: AuthenticatedHttpRequest, article_id: int, article_slug: str
) -> TemplateResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(),
        id=article_id,
        slug=article_slug,
        user=request.user,
    )
    tag_choices = Tag.objects.get_all_choices(request.user)
    if request.method == "POST":
        status, edit_article_form, article = _handle_update(request, article, tag_choices)
    else:
        status = HTTPStatus.OK
        edit_article_form = EditArticleForm(
            initial={
                "tags": article.article_tags.get_selected_values(),
                "title": article.title,
                "reading_time": article.reading_time,
            },
            tag_choices=tag_choices,
        )

    return TemplateResponse(
        request,
        "reading/article_details.html",
        {
            "base": {
                "fluid_content": True,
            },
            "article": article,
            "edit_article_form": edit_article_form,
            "from_url": get_from_url_for_article_details(request, request.GET),
        },
        status=status,
    )


def _handle_update(
    request: AuthenticatedHttpRequest, article: Article, tag_choices: FormChoices
) -> tuple[HTTPStatus, EditArticleForm, Article]:
    form = EditArticleForm(
        request.POST,
        initial={
            "tags": article.article_tags.get_selected_values(),
            "title": article.title,
            "reading_time": article.reading_time,
        },
        tag_choices=tag_choices,
    )
    status = HTTPStatus.BAD_REQUEST
    if form.is_valid():
        status = HTTPStatus.OK
        with transaction.atomic():
            tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data.pop("tags"))
            ArticleTag.objects.associate_articles_with_tags(
                [article], tags, constants.TaggingReason.ADDED_MANUALLY, readd_deleted=True
            )
            ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)
            article.update_from_details(**form.cleaned_data)
            article.save()

    # Refresh the many-to-many relationship of tags to display the latest value.
    return status, form, Article.objects.get_queryset().for_details().get(id=article.id)
