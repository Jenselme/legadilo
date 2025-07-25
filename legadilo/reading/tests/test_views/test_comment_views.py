# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.reading.models import Article, Comment
from legadilo.reading.tests.factories import CommentFactory

COMMENT = """My comment
with <em>nasty HTML</em>
and line breaks
"""
CLEANED_COMMENT = """My comment
with nasty HTML
and line breaks"""


@pytest.mark.django_db
class TestCreateCommentView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("reading:create_comment")

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert_redirected_to_login_page(response)

    def test_get(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED

    def test_create_invalid_user(self, logged_in_sync_client, other_user):
        article = Article.objects.create(user=other_user)

        response = logged_in_sync_client.post(
            self.url, data={"article_id": article.id, "text": "My comment"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_create_invalid_form(self, logged_in_sync_client, other_user):
        response = logged_in_sync_client.post(self.url, data={})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create(self, logged_in_sync_client, user, django_assert_num_queries):
        article = Article.objects.create(user=user)

        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(
                self.url,
                data={
                    "article_id": article.id,
                    "text": COMMENT,
                },
            )

        assert response.status_code == HTTPStatus.OK
        assert article.comments.count() == 1
        comment = article.comments.get()
        assert comment.text == CLEANED_COMMENT


@pytest.mark.django_db
class TestDisplayCommentView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.comment = CommentFactory(article__user=user)
        self.url = reverse("reading:display_comment", kwargs={"pk": self.comment.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_display_invalid_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_display(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
class TestEditCommentView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.comment = CommentFactory(article__user=user)
        self.url = reverse("reading:edit_comment", kwargs={"pk": self.comment.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_edit_invalid_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_edit_form(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context_data["comment"] == self.comment

    def test_edit(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(self.url, data={"text": "Updated text"})

        assert response.status_code == HTTPStatus.OK
        self.comment.refresh_from_db()
        assert self.comment.text == "Updated text"


@pytest.mark.django_db
class TestDeleteCommentView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.comment = CommentFactory(article__user=user)
        self.url = reverse("reading:delete_comment", kwargs={"pk": self.comment.id})

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert_redirected_to_login_page(response)

    def test_edit_invalid_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.OK
        assert Comment.objects.count() == 0
