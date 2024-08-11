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

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from legadilo.reading import constants
from legadilo.reading.models import Article
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.security import full_sanitize


class SearchForm(forms.Form):
    # Main fields.
    q = forms.CharField(required=True, min_length=4, label=_("Search query"))
    search_type = forms.ChoiceField(
        required=False,
        choices=constants.ArticleSearchType.choices,
        initial=constants.ArticleSearchType.PLAIN.value,
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


@require_GET  # type: ignore[type-var]
@login_required
async def search_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    form = SearchForm(request.GET)
    articles: list[Article] = []
    total_results = 0
    if form.is_valid():
        articles, total_results = await Article.objects.search(
            request.user, form.cleaned_data["q"], form.cleaned_data["search_type"]
        )

    return TemplateResponse(
        request,
        "reading/search.html",
        {
            "form": form,
            "articles": articles,
            "total_results": total_results,
        },
    )
