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

from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleDataFactory
from legadilo.reading.tests.fixtures import get_article_fixture_content


@pytest.mark.django_db
class TestCreateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("api-1.0.0:create_article")
        self.article_link = "https://example.com/articles/legadilo.html"

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_create_article_empty_payload(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {"type": "missing", "loc": ["body", "article", "link"], "msg": "Field required"}
            ]
        }

    def test_create_article_invalid_data(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(
            self.url,
            {"link": self.article_link, "content": "Some content"},
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "ctx": {
                        "error": "You must supply either both title and content or none of them"
                    },
                    "loc": ["body", "article"],
                    "msg": "Value error, You must supply either both title and content or none of them",  # noqa: E501
                    "type": "value_error",
                }
            ]
        }

    def test_create_article_from_link_only(
        self, django_assert_num_queries, logged_in_sync_client, mocker
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(link=self.article_link),
        )

        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(
                self.url, {"link": self.article_link}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.OK
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.link == self.article_link
        mocked_get_article_from_url.assert_called_once_with(self.article_link)

    def test_create_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, mocker
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(link=self.article_link),
        )

        with django_assert_num_queries(15):
            response = logged_in_sync_client.post(
                self.url,
                {"link": self.article_link, "tags": ["Some tag"]},
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.link == self.article_link
        assert list(article.tags.all().values_list("title", flat=True)) == ["Some tag"]
        mocked_get_article_from_url.assert_called_once_with(self.article_link)

    def test_create_article_from_data(
        self, django_assert_num_queries, logged_in_sync_client, mocker
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(link=self.article_link),
        )

        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "link": self.article_link,
                    "content": get_article_fixture_content("sample_blog_article.html"),
                    "title": "My article",
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.link == "https://www.example.com/posts/en/1-super-article/"
        assert article.title == "My article"
        assert article.content.startswith("<article>\n")
        assert (
            article.summary
            == "I just wrote a new book, I’ll hope you will like it! Here are some thoughts on it."  # noqa: RUF001 String contains ambiguous
        )
        assert article.table_of_content == []
        assert not mocked_get_article_from_url.called
