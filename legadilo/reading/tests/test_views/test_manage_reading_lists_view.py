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

from legadilo.reading import constants
from legadilo.reading.models import ReadingList, ReadingListTag
from legadilo.reading.tests.factories import ReadingListFactory, TagFactory


@pytest.mark.django_db
class TestReadingListsAdminView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("reading:reading_lists_admin")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_get_page(self, logged_in_sync_client, user, other_user):
        reading_list = ReadingListFactory(user=user)
        ReadingListFactory(user=other_user)

        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/reading_lists_admin.html"
        assert list(response.context_data["reading_lists"]) == [reading_list]


@pytest.mark.django_db
class TestCreateReadingListView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("reading:create_reading_list")
        self.tag_to_include = TagFactory(slug="tag-to-include")
        self.tag_to_exclude = TagFactory(slug="tag-to-exclude")
        self.sample_data = {
            "title": "Sample Reading List",
            "enable_reading_on_scroll": True,
            "auto_refresh_interval": 0,
            "order": 12,
            "read_status": constants.ReadStatus.ONLY_READ,
            "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
            "for_later_status": constants.ForLaterStatus.ONLY_NOT_FOR_LATER,
            "articles_max_age_value": 0,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS,
            "articles_reading_time": 15,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN,
            "tags_to_include": ["New tag", self.tag_to_include.slug],
            "include_tag_operator": constants.ReadingListTagOperator.ANY,
            "tags_to_exclude": [self.tag_to_exclude.slug],
            "exclude_tag_operator": constants.ReadingListTagOperator.ANY,
            "order_direction": constants.ReadingListOrderDirection.ASC,
        }

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, data={})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_reading_list(self, logged_in_sync_client, user):
        response = logged_in_sync_client.post(self.url, data=self.sample_data)

        reading_list = ReadingList.objects.get()
        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse(
            "reading:edit_reading_list", kwargs={"reading_list_id": reading_list.id}
        )
        assert reading_list.title == "Sample Reading List"
        assert reading_list.user == user
        assert list(reading_list.reading_list_tags.values_list("tag__slug", "filter_type")) == [
            ("new-tag", constants.ReadingListTagFilterType.INCLUDE),
            (self.tag_to_include.slug, constants.ReadingListTagFilterType.INCLUDE),
            (self.tag_to_exclude.slug, constants.ReadingListTagFilterType.EXCLUDE),
        ]
        for field, value in self.sample_data.items():
            if field in {"tags_to_include", "tags_to_exclude"}:
                continue

            assert getattr(reading_list, field) == value


@pytest.mark.django_db
class TestReadingListEditView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.include_tag = TagFactory(user=user, slug="include-tag")
        ReadingListTag.objects.create(
            tag=self.include_tag,
            reading_list=self.reading_list,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        self.exclude_tag = TagFactory(user=user, slug="exclude-tag")
        ReadingListTag.objects.create(
            tag=self.exclude_tag,
            reading_list=self.reading_list,
            filter_type=constants.ReadingListTagFilterType.INCLUDE,
        )
        self.url = reverse(
            "reading:edit_reading_list", kwargs={"reading_list_id": self.reading_list.id}
        )
        self.sample_data = {
            "title": "Sample Reading List",
            "enable_reading_on_scroll": True,
            "auto_refresh_interval": 0,
            "order": 12,
            "read_status": constants.ReadStatus.ONLY_READ,
            "favorite_status": constants.FavoriteStatus.ONLY_FAVORITE,
            "for_later_status": constants.ForLaterStatus.ONLY_NOT_FOR_LATER,
            "articles_max_age_value": 0,
            "articles_max_age_unit": constants.ArticlesMaxAgeUnit.WEEKS,
            "articles_reading_time": 15,
            "articles_reading_time_operator": constants.ArticlesReadingTimeOperator.LESS_THAN,
            "tags_to_include": ["New tag", self.include_tag.slug],
            "include_tag_operator": constants.ReadingListTagOperator.ANY,
            "tags_to_exclude": [self.exclude_tag.slug],
            "exclude_tag_operator": constants.ReadingListTagOperator.ANY,
            "order_direction": constants.ReadingListOrderDirection.ASC,
        }

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_edit_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url, data=self.sample_data)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, data={})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_update(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, data=self.sample_data)

        assert response.status_code == HTTPStatus.OK
        assert list(
            self.reading_list.reading_list_tags.values_list("tag__slug", "filter_type")
        ) == [
            ("new-tag", "INCLUDE"),
            (self.include_tag.slug, "INCLUDE"),
            (self.exclude_tag.slug, "EXCLUDE"),
        ]
        self.reading_list.refresh_from_db()
        for field, value in self.sample_data.items():
            if field in {"tags_to_include", "tags_to_exclude"}:
                continue

            assert getattr(self.reading_list, field) == value
