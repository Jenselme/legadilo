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
from legadilo.reading.models import Article


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
                self.url, data={"article_id": article.id, "text": "My comment"}
            )

        assert response.status_code == HTTPStatus.OK
        assert article.comments.count() == 1
        comment = article.comments.get()
        assert comment.text == "My&#32;comment"
