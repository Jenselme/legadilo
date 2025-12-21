# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading.tests.factories import (
    ArticleFactory,
    ArticlesGroupFactory,
    ReadingListFactory,
    TagFactory,
)


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

        assert_redirected_to_login_page(response)

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
        with django_assert_num_queries(13):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context_data["article"] == self.article
        assert response.context_data["from_url"] == reverse("reading:default_reading_list")
        assert "edit_article_form" in response.context_data

    def test_view_details_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        from_url = "/reading/lists/unread/"
        with django_assert_num_queries(13):
            response = logged_in_sync_client.get(self.url, data={"from_url": from_url})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/article_details.html"
        assert response.context_data["article"] == self.article
        assert response.context_data["from_url"] == from_url
        assert "edit_article_form" in response.context_data


@pytest.mark.django_db
class TestUpdateArticleDetailsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.reading_list = ReadingListFactory(user=user)
        self.tag_to_keep = TagFactory(user=user)
        self.tag_to_delete = TagFactory(user=user)
        self.article.tags.add(self.tag_to_keep, self.tag_to_delete)
        self.deleted_tag_to_readd = TagFactory(user=user)
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

        assert_redirected_to_login_page(response)

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
        with django_assert_num_queries(30):
            response = logged_in_sync_client.post(
                self.url,
                {**self.sample_payload, "for_article_details": True},
            )

        assert response.status_code == HTTPStatus.OK
        assert list(self.article.article_tags.values_list("tag__slug", flat=True)) == [
            "some-tag",
            self.tag_to_keep.slug,
            self.deleted_tag_to_readd.slug,
            self.existing_tag_to_add.slug,
        ]

    def test_update_other_values_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        initial_slug = self.article.slug

        with django_assert_num_queries(30):
            response = logged_in_sync_client.post(
                self.url, {**self.sample_payload, "title": "Updated title", "reading_time": 666}
            )

        assert response.status_code == HTTPStatus.OK
        self.article.refresh_from_db()
        assert self.article.title == "Updated title"
        assert self.article.slug == initial_slug
        assert self.article.reading_time == 666

    def test_empty_tags(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {**self.sample_payload, "tags": [""]})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.context_data["edit_article_form"].errors == {
            "tags": ["Tag cannot be empty."],
        }

    def test_tags_only_special_char(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {**self.sample_payload, "tags": ["&"]})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.context_data["edit_article_form"].errors == {
            "tags": ["Tag cannot contain only spaces or special characters."]
        }

    def test_link_to_group(self, user, logged_in_sync_client, django_assert_num_queries):
        group = ArticlesGroupFactory(user=user)
        ArticleFactory(user=user)

        with django_assert_num_queries(36):
            response = logged_in_sync_client.post(
                self.url, {**self.sample_payload, "group": group.id}
            )

        assert response.status_code == HTTPStatus.OK
        self.article.refresh_from_db()
        assert self.article.group == group

    def test_unlink_from_group(self, user, logged_in_sync_client, django_assert_num_queries):
        group = ArticlesGroupFactory(user=user)
        ArticleFactory(user=user, group=group)

        with django_assert_num_queries(30):
            response = logged_in_sync_client.post(self.url, {**self.sample_payload})

        assert response.status_code == HTTPStatus.OK
        self.article.refresh_from_db()
        assert self.article.group_id is None

    def test_link_to_group_of_other_user(self, user, other_user, logged_in_sync_client):
        group = ArticlesGroupFactory(user=other_user)
        ArticleFactory(user=user, group=group)

        response = logged_in_sync_client.post(self.url, {**self.sample_payload, "group": group.id})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        self.article.refresh_from_db()
        assert self.article.group_id is None
