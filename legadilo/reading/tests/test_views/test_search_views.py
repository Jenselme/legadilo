# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading import constants
from legadilo.reading.models import ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, TagFactory
from legadilo.reading.views.search_views import SearchForm


class TestSearchForm:
    def test_without_data(self):
        form = SearchForm({}, tag_choices=[])

        assert not form.is_valid()
        assert form.errors == {"q": ["This field is required."]}

    def test_with_only_q(self):
        form = SearchForm({"q": "Claudius"}, tag_choices=[])

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PLAIN,
            "order": constants.ArticleSearchOrderBy.RANK_DESC,
            "read_status": constants.ReadStatus.ALL,
            "favorite_status": constants.FavoriteStatus.ALL,
            "for_later_status": constants.ForLaterStatus.ALL,
            "articles_max_age_value": None,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.UNSET,
            "articles_reading_time": None,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.UNSET,
            "include_tag_operator": constants.ReadingListTagOperator.ALL,
            "tags_to_include": [],
            "exclude_tag_operator": constants.ReadingListTagOperator.ALL,
            "tags_to_exclude": [],
        }

    def test_q_cleaning(self):
        form = SearchForm({"q": "<span>Claudius</span>"}, tag_choices=[])

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PLAIN,
            "order": constants.ArticleSearchOrderBy.RANK_DESC,
            "read_status": constants.ReadStatus.ALL,
            "favorite_status": constants.FavoriteStatus.ALL,
            "for_later_status": constants.ForLaterStatus.ALL,
            "articles_max_age_value": None,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.UNSET,
            "articles_reading_time": None,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.UNSET,
            "include_tag_operator": constants.ReadingListTagOperator.ALL,
            "tags_to_include": [],
            "exclude_tag_operator": constants.ReadingListTagOperator.ALL,
            "tags_to_exclude": [],
        }

    def test_q_cleaning_result_too_small_after_cleaning(self):
        form = SearchForm({"q": "<span>C</span>"}, tag_choices=[])

        assert not form.is_valid()
        assert form.errors == {
            "q": ["You must at least enter 3 characters"],
        }

    def test_advanced_values_set_unit_and_operator_unset(self):
        form = SearchForm(
            {
                "q": "Claudius",
                "articles_max_age_value": 12,
                "articles_reading_time": 12,
            },
            tag_choices=[],
        )

        assert not form.is_valid()
        assert form.errors == {
            "__all__": [
                "You must set the max age unit when searching by max age",
                "You must supply a reading time operator when searching by reading time",
            ]
        }

    def test_advanced_values_unset_unit_and_operator_set(self):
        form = SearchForm(
            {
                "q": "Claudius",
                "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS.value,
                "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN.value,  # noqa: E501
            },
            tag_choices=[],
        )

        assert not form.is_valid()
        assert form.errors == {
            "__all__": [
                "You must supply a max age value when searching by max age",
                "You must supply a reading time when searching by reading time",
            ]
        }

    def test_everything_filled(self):
        form = SearchForm(
            {
                "q": "Claudius",
                "search_type": constants.ArticleSearchType.PHRASE,
                "order": constants.ArticleSearchOrderBy.READ_AT_ASC,
                "read_status": constants.ReadStatus.ONLY_READ.value,
                "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE.value,
                "for_later_status": constants.ForLaterStatus.ONLY_FOR_LATER.value,
                "articles_max_age_value": 12,
                "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS.value,
                "articles_reading_time": 12,
                "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN.value,  # noqa: E501
                "include_tag_operator": constants.ReadingListTagOperator.ALL.value,
                "tags_to_include": ["some-tag"],
                "exclude_tag_operator": constants.ReadingListTagOperator.ANY.value,
                "tags_to_exclude": ["other-tag"],
            },
            tag_choices=[("some-tag", "Some tag"), ("other-tag", "Other tag")],
        )

        assert form.is_valid()
        assert form.cleaned_data == {
            "q": "Claudius",
            "search_type": constants.ArticleSearchType.PHRASE,
            "order": constants.ArticleSearchOrderBy.READ_AT_ASC,
            "read_status": constants.ReadStatus.ONLY_READ,
            "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
            "for_later_status": constants.ForLaterStatus.ONLY_FOR_LATER,
            "articles_max_age_value": 12,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS,
            "articles_reading_time": 12,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN,
            "include_tag_operator": constants.ReadingListTagOperator.ALL,
            "tags_to_include": ["some-tag"],
            "exclude_tag_operator": constants.ReadingListTagOperator.ANY,
            "tags_to_exclude": ["other-tag"],
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

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.template_name == "reading/search.html"
        assert not response.context_data["search_form"].is_valid()
        assert response.context_data["search_form"].errors == {"q": ["This field is required."]}
        assert response.context_data["articles"] == []
        assert response.context_data["total_results"] == 0

    def test_search(self, user, logged_in_sync_client):
        article = ArticleFactory(title="Claudius", user=user)
        ArticleFactory(user=user)

        response = logged_in_sync_client.get(self.url, data={"q": "Claudius"})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert response.context_data["search_form"].is_valid()
        assert response.context_data["articles"] == [article]
        assert response.context_data["total_results"] == 1

    def test_search_with_url(self, user, logged_in_sync_client):
        article_url = "https://example.com/articles/1.html"
        article = ArticleFactory(title="Claudius", user=user, url=article_url)

        response = logged_in_sync_client.get(self.url, data={"q": article_url})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert response.context_data["search_form"].is_valid()
        assert response.context_data["search_form"].data == {
            "q": ["https://example.com/articles/1.html"],
            "search_type": [constants.ArticleSearchType.URL],
        }
        assert response.context_data["articles"] == [article]

    def test_search_with_tags(self, user, logged_in_sync_client):
        ArticleFactory(user=user, title="Claudius")
        tag_to_include = TagFactory(user=user)
        tag_to_exclude = TagFactory(user=user)
        article_with_tag_to_include = ArticleFactory(user=user, title="Claudius")
        ArticleTag.objects.create(
            article=article_with_tag_to_include,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_with_tag_to_exclude = ArticleFactory(user=user, title="Claudius")
        ArticleTag.objects.create(
            article=article_with_tag_to_exclude,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )

        response = logged_in_sync_client.get(
            self.url,
            data={
                "q": "Claudius",
                "tags_to_include": [tag_to_include.slug],
                "tags_to_exclude": [tag_to_exclude.slug],
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert response.context_data["search_form"].is_valid()
        assert response.context_data["articles"] == [article_with_tag_to_include]
        assert response.context_data["total_results"] == 1

    def test_update_search(self, user, logged_in_sync_client):
        ArticleFactory(user=user, title="Claudius")
        tag_to_include = TagFactory(user=user)
        tag_to_exclude = TagFactory(user=user)
        article_with_tag_to_include = ArticleFactory(user=user, title="Claudius")
        ArticleTag.objects.create(
            article=article_with_tag_to_include,
            tag=tag_to_include,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        article_with_tag_to_exclude = ArticleFactory(user=user, title="Claudius")
        ArticleTag.objects.create(
            article=article_with_tag_to_exclude,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        get_data = urlencode(
            {
                "q": "Claudius",
                "tags_to_include": [tag_to_include.slug],
                "tags_to_exclude": [tag_to_exclude.slug],
            },
            doseq=True,
        )

        response = logged_in_sync_client.post(
            f"{self.url}?{get_data}",
            data={
                "update_action": constants.UpdateArticleActions.MARK_AS_READ.value,
                "add_tags": ["New tag"],
            },
        )

        article_with_tag_to_include.refresh_from_db()
        assert article_with_tag_to_include.is_read
        assert list(
            article_with_tag_to_include.tags.order_by("slug").values_list("slug", flat=True)
        ) == [
            "new-tag",
            tag_to_include.slug,
        ]
        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/search.html"
        assert response.context_data["search_form"].is_valid()
        assert response.context_data["articles"] == [article_with_tag_to_include]
        assert response.context_data["total_results"] == 1
