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
from legadilo.reading.models import ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory, TagFactory


@pytest.mark.django_db
class TestArticleDetailsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "reading:article_details",
            kwargs={"article_id": self.article.id, "article_slug": self.article.slug},
        )

    def test_view_details_if_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_view_details_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_cannot_get_if_slug_is_invalid(self, logged_in_sync_client):
        url = reverse(
            "reading:article_details",
            kwargs={"article_id": self.article.id, "article_slug": "toto"},
        )

        response = logged_in_sync_client.get(url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_view_details(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context["article"] == self.article
        assert response.context["from_url"] == reverse("reading:default_reading_list")
        assert "edit_article_form" in response.context

    def test_view_details_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        from_url = "/reading/lists/unread/"
        with django_assert_num_queries(9):
            response = logged_in_sync_client.get(self.url, data={"from_url": from_url})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context["article"] == self.article
        assert response.context["from_url"] == from_url
        assert "edit_article_form" in response.context


@pytest.mark.django_db
class TestUpdateArticleDetailsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.reading_list = ReadingListFactory(user=user)
        self.tag_to_keep = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.tag_to_keep,
            article=self.article,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        self.tag_to_delete = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.tag_to_delete,
            article=self.article,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        self.deleted_tag_to_readd = TagFactory(user=user)
        ArticleTag.objects.create(
            tag=self.deleted_tag_to_readd,
            article=self.article,
            tagging_reason=constants.TaggingReason.DELETED,
        )
        self.existing_tag_to_add = TagFactory(user=user)
        self.some_other_tag = TagFactory(user=user)
        self.url = reverse(
            "reading:article_details",
            kwargs={
                "article_id": self.article.id,
                "article_slug": self.article.slug,
            },
        )
        self.sample_payload = {
            "tags": [
                self.tag_to_keep.slug,
                self.existing_tag_to_add.slug,
                self.deleted_tag_to_readd.slug,
                "Some tag",
            ],
            "title": self.article.title,
            "reading_time": self.article.reading_time,
        }

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_access_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_invalid_form(self, logged_in_sync_client):
        payload = self.sample_payload.copy()
        del payload["reading_time"]
        payload["title"] = "Updated title"

        response = logged_in_sync_client.post(self.url, payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        self.article.refresh_from_db()
        assert self.article.title != "Updated title"

    def test_update_tags_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(23):
            response = logged_in_sync_client.post(
                self.url,
                {**self.sample_payload, "for_article_details": True},
            )

        assert response.status_code == HTTPStatus.OK
        assert list(self.article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("some-tag", constants.TaggingReason.ADDED_MANUALLY),
            (self.tag_to_keep.slug, constants.TaggingReason.ADDED_MANUALLY),
            (self.tag_to_delete.slug, constants.TaggingReason.DELETED),
            (self.deleted_tag_to_readd.slug, constants.TaggingReason.ADDED_MANUALLY),
            (self.existing_tag_to_add.slug, constants.TaggingReason.ADDED_MANUALLY),
        ]

    def test_update_other_values_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        initial_slug = self.article.slug

        with django_assert_num_queries(23):
            response = logged_in_sync_client.post(
                self.url, {**self.sample_payload, "title": "Updated title", "reading_time": 666}
            )

        assert response.status_code == HTTPStatus.OK
        self.article.refresh_from_db()
        assert self.article.title == "Updated title"
        assert self.article.slug == initial_slug
        assert self.article.reading_time == 666
