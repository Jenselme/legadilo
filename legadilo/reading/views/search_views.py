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
import asyncio
from http import HTTPStatus

from asgiref.sync import sync_to_async
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms import FormChoices
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.forms.widgets import MultipleTagsWidget
from legadilo.reading import constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.models.article import (
    ArticleFullTextSearchQuery,
    ArticleQuerySet,
    ArticleTagSearch,
)
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.security import full_sanitize

from ...users.models import User
from ...utils.collections_utils import alist, aset
from ...utils.validators import is_url_valid
from .list_of_articles_views import UpdateArticlesForm, update_list_of_articles


class SearchForm(forms.Form):
    # Main fields.
    q = forms.CharField(required=True, min_length=4, label=_("Search query"))
    search_type = forms.ChoiceField(
        required=False,
        choices=constants.ArticleSearchType.choices,
        initial=constants.ArticleSearchType.PLAIN,
    )
    # Dates
    order = forms.ChoiceField(
        required=False,
        choices=constants.ArticleSearchOrderBy.choices,
        initial=constants.ArticleSearchOrderBy.RANK_DESC,
    )
    # Search refinement fields
    read_status = forms.ChoiceField(
        required=False, choices=constants.ReadStatus.choices, initial=constants.ReadStatus.ALL
    )
    favorite_status = forms.ChoiceField(
        required=False,
        choices=constants.FavoriteStatus.choices,
        initial=constants.FavoriteStatus.ALL,
    )
    for_later_status = forms.ChoiceField(
        required=False,
        choices=constants.ForLaterStatus.choices,
        initial=constants.ForLaterStatus.ALL,
    )
    articles_max_age_value = forms.IntegerField(required=False, min_value=0)
    articles_max_age_unit = forms.ChoiceField(
        required=False,
        choices=constants.ArticlesMaxAgeUnit.choices,
        initial=constants.ArticlesMaxAgeUnit.UNSET,
    )
    articles_reading_time = forms.IntegerField(required=False, min_value=0)
    articles_reading_time_operator = forms.ChoiceField(
        required=False,
        choices=constants.ArticlesReadingTimeOperator.choices,
        initial=constants.ArticlesReadingTimeOperator.UNSET,
    )
    # Tags
    include_tag_operator = forms.ChoiceField(
        required=False,
        choices=constants.ReadingListTagOperator.choices,
        initial=constants.ReadingListTagOperator.ALL,
        help_text=_("Articles to include must have all or any of the supplied tags."),
    )
    tags_to_include = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_("Articles with these tags will be included in the search."),
        widget=MultipleTagsWidget(allow_new=False),
    )
    exclude_tag_operator = forms.ChoiceField(
        required=False,
        choices=constants.ReadingListTagOperator.choices,
        initial=constants.ReadingListTagOperator.ALL,
        help_text=_("Articles to exclude must have all or any of the supplied tags."),
    )
    tags_to_exclude = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_("Articles with these tags will be excluded from the search."),
        widget=MultipleTagsWidget(allow_new=False),
    )

    def __init__(self, data=None, *, tag_choices: FormChoices):
        super().__init__(data.copy())
        self.fields["tags_to_include"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["tags_to_exclude"].choices = tag_choices  # type: ignore[attr-defined]

        # Make sure we set the proper search type is correct when we do a URL search. By default,
        # it's a word search.
        search_type = self.data.get("search_type")
        if is_url_valid(self.data.get("q")) and not search_type:
            self.data["search_type"] = constants.ArticleSearchType.URL  # type: ignore[index]

    def clean_q(self):
        q = self.cleaned_data["q"]
        q = full_sanitize(q)
        if len(q) < self.fields["q"].min_length:  # type: ignore[attr-defined]
            raise ValidationError(
                "You must at least enter 3 characters", code="q-too-short-after-cleaning"
            )

        return q

    def clean_search_type(self):
        if not self.cleaned_data.get("search_type"):
            return constants.ArticleSearchType.PLAIN
        return constants.ArticleSearchType(self.cleaned_data["search_type"])

    def clean_order(self):
        if not self.cleaned_data.get("order"):
            return constants.ArticleSearchOrderBy.RANK_DESC
        return constants.ArticleSearchOrderBy(self.cleaned_data["order"])

    def clean_read_status(self):
        if not self.cleaned_data.get("read_status"):
            return constants.ReadStatus.ALL

        return constants.ReadStatus(self.cleaned_data["read_status"])

    def clean_favorite_status(self):
        if not self.cleaned_data.get("favorite_status"):
            return constants.FavoriteStatus.ALL

        return constants.FavoriteStatus(self.cleaned_data["favorite_status"])

    def clean_for_later_status(self):
        if not self.cleaned_data.get("for_later_status"):
            return constants.ForLaterStatus.ALL

        return constants.ForLaterStatus(self.cleaned_data["for_later_status"])

    def clean_articles_max_age_unit(self):
        if not self.cleaned_data.get("articles_max_age_unit"):
            return constants.ArticlesMaxAgeUnit.UNSET

        return constants.ArticlesMaxAgeUnit(self.cleaned_data["articles_max_age_unit"])

    def clean_articles_reading_time_operator(self):
        if not self.cleaned_data.get("articles_reading_time_operator"):
            return constants.ArticlesReadingTimeOperator.UNSET

        return constants.ArticlesReadingTimeOperator(
            self.cleaned_data["articles_reading_time_operator"]
        )

    def clean_include_tag_operator(self):
        if not self.cleaned_data.get("include_tag_operator"):
            return constants.ReadingListTagOperator.ALL

        return constants.ReadingListTagOperator(self.cleaned_data["include_tag_operator"])

    def clean_exclude_tag_operator(self):
        if not self.cleaned_data.get("exclude_tag_operator"):
            return constants.ReadingListTagOperator.ALL

        return constants.ReadingListTagOperator(self.cleaned_data["exclude_tag_operator"])

    def clean(self):
        super().clean()
        errors = []

        is_articles_max_age_unit_set = (
            articles_max_age_unit := self.cleaned_data.get("articles_max_age_unit")
        ) and articles_max_age_unit != constants.ArticlesMaxAgeUnit.UNSET
        is_articles_max_age_value_set = bool(self.cleaned_data.get("articles_max_age_value"))
        if is_articles_max_age_unit_set and not is_articles_max_age_value_set:
            errors.append(
                ValidationError(
                    _("You must supply a max age value when searching by max age"),
                    code="max-age-value-unset-but-unit-is",
                )
            )
        elif not is_articles_max_age_unit_set and is_articles_max_age_value_set:
            errors.append(
                ValidationError(
                    _("You must set the max age unit when searching by max age"),
                    code="max-age-unit-unset-but-value-is",
                ),
            )

        is_articles_reading_time_operator_set = (
            articles_reading_time_operator := self.cleaned_data.get(
                "articles_reading_time_operator"
            )
        ) and articles_reading_time_operator != constants.ArticlesReadingTimeOperator.UNSET
        is_articles_reading_time_set = bool(self.cleaned_data.get("articles_reading_time"))
        if is_articles_reading_time_operator_set and not is_articles_reading_time_set:
            errors.append(
                ValidationError(
                    _("You must supply a reading time when searching by reading time"),
                    code="reading-time-unset-but-operator-is",
                )
            )
        elif not is_articles_reading_time_operator_set and is_articles_reading_time_set:
            errors.append(
                ValidationError(
                    _("You must supply a reading time operator when searching by reading time"),
                    code="reading-operator-unset-but-value-is",
                )
            )

        if len(errors):
            raise ValidationError(errors)


@require_http_methods(["GET", "POST"])  # type: ignore[type-var]
@login_required
async def search_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    status = HTTPStatus.OK
    tag_choices = await sync_to_async(Tag.objects.get_all_choices)(request.user)
    search_form = SearchForm(request.GET, tag_choices=tag_choices)
    update_articles_form = UpdateArticlesForm(request.POST, tag_choices=tag_choices)
    # We don't do anything unless we have a valid search.
    if not search_form.is_valid():
        return TemplateResponse(
            request,
            "reading/search.html",
            {
                "search_form": search_form,
                "update_articles_form": update_articles_form,
                "articles": [],
                "total_results": 0,
            },
            status=HTTPStatus.BAD_REQUEST,
        )

    if request.method == "POST":
        # We update the articles of the current search.
        articles_qs = await _search(request.user, search_form)
        # articles_qs is based on a union, so we can't rely on filter or paginators. Since we need
        # these features, we extract the ids of the articles to update and build a new QS.
        article_ids_to_update = await aset(articles_qs.values_list("id", flat=True))
        status, update_articles_form = await sync_to_async(update_list_of_articles)(
            request,
            Article.objects.get_queryset().filter(id__in=article_ids_to_update),
            tag_choices,
        )

    # Articles have been updated. Some may not be part of the search anymore. Rerun it.
    articles_qs = await _search(request.user, search_form)
    articles, total_results = await asyncio.gather(
        alist(articles_qs[: constants.MAX_ARTICLES_PER_PAGE]), articles_qs.acount()
    )

    return TemplateResponse(
        request,
        "reading/search.html",
        {
            "search_form": search_form,
            "update_articles_form": update_articles_form,
            "articles": articles,
            "total_results": total_results,
        },
        status=status,
    )


async def _search(user: User, search_form: SearchForm) -> ArticleQuerySet:
    tags_to_include = search_form.cleaned_data.get("tags_to_include", [])
    tags_to_exclude = search_form.cleaned_data.get("tags_to_exclude", [])
    all_slugs = {
        *(tag_slug for tag_slug in tags_to_include),
        *(tag_slug for tag_slug in tags_to_exclude),
    }
    tag_slugs_to_ids = await sync_to_async(Tag.objects.get_slugs_to_ids)(user, all_slugs)
    form_data = {
        key: value
        for key, value in search_form.cleaned_data.items()
        if key not in {"tags_to_include", "tags_to_exclude"}
    }
    query = ArticleFullTextSearchQuery(
        **form_data,
        tags=_build_tags(tag_slugs_to_ids, tags_to_include, tags_to_exclude),
    )
    return Article.objects.search(user, query)


def _build_tags(
    tag_slugs_to_ids: dict[str, int], tags_to_include: list[str], tags_to_exclude: list[str]
) -> list[ArticleTagSearch]:
    return [
        *(
            ArticleTagSearch(
                filter_type=constants.ReadingListTagFilterType.INCLUDE,
                tag_id=tag_slugs_to_ids[tag_slug],
            )
            for tag_slug in tags_to_include
            if tag_slug in tag_slugs_to_ids
        ),
        *(
            ArticleTagSearch(
                filter_type=constants.ReadingListTagFilterType.EXCLUDE,
                tag_id=tag_slugs_to_ids[tag_slug],
            )
            for tag_slug in tags_to_exclude
            if tag_slug in tag_slugs_to_ids
        ),
    ]
