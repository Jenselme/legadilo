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

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading import constants
from legadilo.reading.tests.factories import ArticleFactory
from legadilo.reading.views.search_views import SearchForm


class TestSearchForm:
    def test_without_data(self):
        form = SearchForm({})

        assert not form.is_valid()
        assert form.errors == {"q": ["This field is required."]}

    def test_with_only_q(self):
        form = SearchForm({"q": "Claudius"})

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PLAIN,
            "read_status": constants.ReadStatus.ALL,
            "favorite_status": constants.FavoriteStatus.ALL,
            "for_later_status": constants.ForLaterStatus.ALL,
            "articles_max_age_value": None,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.UNSET,
            "articles_reading_time": None,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.UNSET,
        }

    def test_q_cleaning(self):
        form = SearchForm({"q": "<span>Claudius</span>"})

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PLAIN,
            "read_status": constants.ReadStatus.ALL,
            "favorite_status": constants.FavoriteStatus.ALL,
            "for_later_status": constants.ForLaterStatus.ALL,
            "articles_max_age_value": None,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.UNSET,
            "articles_reading_time": None,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.UNSET,
        }

    def test_q_cleaning_result_too_small_after_cleaning(self):
        form = SearchForm({"q": "<span>C</span>"})

        assert not form.is_valid()
        assert form.errors == {
            "q": ["You must at least enter 3 characters"],
        }

    def test_advanced_values_set_unit_and_operator_unset(self):
        form = SearchForm({
            "q": "Claudius",
            "articles_max_age_value": 12,
            "articles_reading_time": 12,
        })

        assert not form.is_valid()
        assert form.errors == {
            "__all__": [
                "You must set the max age unit when searching by max age",
                "You must supply a reading time operator when searching by reading time",
            ]
        }

    def test_advanced_values_unset_unit_and_operator_set(self):
        form = SearchForm({
            "q": "Claudius",
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS.value,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN.value,
        })

        assert not form.is_valid()
        assert form.errors == {
            "__all__": [
                "You must supply a max age value when searching by max age",
                "You must supply a reading time when searching by reading time",
            ]
        }

    def test_everything_filled(self):
        form = SearchForm({
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PHRASE,
            "read_status": constants.ReadStatus.ONLY_READ.value,
            "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE.value,
            "for_later_status": constants.ForLaterStatus.ONLY_FOR_LATER.value,
            "articles_max_age_value": 12,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS.value,
            "articles_reading_time": 12,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN.value,
        })

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PHRASE,
            "read_status": constants.ReadStatus.ONLY_READ,
            "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
            "for_later_status": constants.ForLaterStatus.ONLY_FOR_LATER,
            "articles_max_age_value": 12,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS,
            "articles_reading_time": 12,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN,
        }


@pytest.mark.django_db
class TestSearchView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("reading:search")

    def test_not_connected(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert not response.context["form"].is_valid()
        assert response.context["form"].errors == {"q": ["This field is required."]}
        assert response.context["articles"] == []
        assert response.context["total_results"] == 0

    def test_search(self, user, logged_in_sync_client):
        article = ArticleFactory(title="Claudius", user=user)
        ArticleFactory(user=user)

        response = logged_in_sync_client.get(self.url, data={"q": "Claudius"})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert response.context["form"].is_valid()
        assert response.context["articles"] == [article]
        assert response.context["total_results"] == 1
