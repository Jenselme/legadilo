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

from http import HTTPStatus
from typing import Any

import pytest
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag
from legadilo.reading.tests.factories import ArticleDataFactory, ArticleFactory, TagFactory
from legadilo.reading.tests.fixtures import get_article_fixture_content
from legadilo.utils.testing import serialize_for_snapshot
from legadilo.utils.time_utils import utcdt, utcnow


def _prepare_article_for_serialization(data: dict[str, Any], article: Article) -> dict[str, Any]:
    data = data.copy()
    assert data["id"] == article.id
    assert data["title"] == article.title
    assert data["slug"] == article.slug
    assert data["external_article_id"] == article.external_article_id
    assert data["url"] == article.url
    assert data["details_url"] == f"http://testserver/reading/articles/{article.id}-{article.slug}/"

    data["id"] = 1
    data["title"] = "Article title"
    data["slug"] = "article-slug"
    data["external_article_id"] = "external-article-id"
    data["url"] = "https://example.com/articles/article.html"
    data["details_url"] = "http://testserver/reading/articles/1-article-slug/"

    return data


@pytest.mark.django_db
class TestCreateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("api-1.0.0:create_article")
        self.article_url = "https://example.com/articles/legadilo.html"

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_create_article_empty_payload(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {"type": "missing", "loc": ["body", "payload", "url"], "msg": "Field required"}
            ]
        }

    def test_create_article_invalid_data(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(
            self.url,
            {"url": self.article_url, "content": "Some content"},
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "ctx": {
                        "error": "You must supply either both title and content or none of them"
                    },
                    "loc": ["body", "payload"],
                    "msg": "Value error, You must supply either both title and content or none of them",  # noqa: E501
                    "type": "value_error",
                }
            ]
        }

    def test_create_article_from_url_only(
        self, django_assert_num_queries, logged_in_sync_client, mocker, snapshot
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(url=self.article_url),
        )

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.url, {"url": self.article_url}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.CREATED
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.url == self.article_url
        mocked_get_article_from_url.assert_called_once_with(self.article_url)
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_article_for_serialization(response.json(), article)),
            "article.json",
        )

    def test_create_article_with_tags(
        self, django_assert_num_queries, logged_in_sync_client, mocker, snapshot
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(url=self.article_url),
        )

        with django_assert_num_queries(17):
            response = logged_in_sync_client.post(
                self.url,
                {"url": self.article_url, "tags": ["Some tag"]},
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.CREATED
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.url == self.article_url
        assert list(article.tags.all().values_list("title", flat=True)) == ["Some tag"]
        mocked_get_article_from_url.assert_called_once_with(self.article_url)
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_article_for_serialization(response.json(), article)),
            "article.json",
        )

    def test_create_article_from_data(
        self, django_assert_num_queries, logged_in_sync_client, mocker, snapshot
    ):
        mocked_get_article_from_url = mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(url=self.article_url),
        )

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "url": self.article_url,
                    "content": get_article_fixture_content("sample_blog_article.html"),
                    "title": "My article",
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.CREATED
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.url == "https://www.example.com/posts/en/1-super-article/"
        assert article.table_of_content == []
        assert not mocked_get_article_from_url.called
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_article_for_serialization(response.json(), article)),
            "article.json",
        )

    def test_try_to_create_existing_article(
        self, user, django_assert_num_queries, logged_in_sync_client, mocker
    ):
        existing_article = ArticleFactory(
            user=user, title="Existing", reading_time=14, url=self.article_url, read_at=utcnow()
        )
        mocker.patch(
            "legadilo.reading.api.get_article_from_url",
            return_value=ArticleDataFactory(
                title="Fetched article",
                url=self.article_url,
                content="Blabla for reading time " * 50,
            ),
        )

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.url, {"url": self.article_url}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.OK
        assert Article.objects.count() == 1
        article = Article.objects.get()
        assert article.url == self.article_url
        assert article.table_of_content == []
        assert article.title == existing_article.title
        assert article.slug == existing_article.slug
        assert article.reading_time == existing_article.reading_time
        assert article.read_at == existing_article.read_at


@pytest.mark.django_db
class TestGetArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(
            user=user,
            published_at=utcdt(2024, 11, 24, 17, 57, 0),
            updated_at=utcdt(2024, 11, 24, 17, 57, 0),
        )
        self.url = reverse("api-1.0.0:get_article", kwargs={"article_id": self.article.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Article.objects.count() == 1

    def test_get(self, user, logged_in_sync_client, snapshot, django_assert_num_queries):
        tag = TagFactory(user=user, title="Some tag")
        tag_to_exclude = TagFactory(user=user, title="Deleted tag")
        ArticleTag.objects.create(
            article=self.article,
            tag=tag,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        )
        ArticleTag.objects.create(
            article=self.article,
            tag=tag_to_exclude,
            tagging_reason=constants.TaggingReason.DELETED,
        )

        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        snapshot.assert_match(
            serialize_for_snapshot(
                _prepare_article_for_serialization(response.json(), self.article)
            ),
            "article.json",
        )


@pytest.mark.django_db
class TestUpdateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(
            user=user,
            published_at=utcdt(2024, 11, 24, 17, 57, 0),
            updated_at=utcdt(2024, 11, 24, 17, 57, 0),
        )
        self.url = reverse("api-1.0.0:update_article", kwargs={"article_id": self.article.id})

    def test_not_logged_in(self, client):
        response = client.patch(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.patch(
            self.url, {}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_no_update(self, logged_in_sync_client, django_assert_num_queries, snapshot):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.patch(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.OK
        snapshot.assert_match(
            serialize_for_snapshot(
                _prepare_article_for_serialization(response.json(), self.article)
            ),
            "article.json",
        )

    def test_update(self, logged_in_sync_client, django_assert_num_queries, snapshot):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.patch(
                self.url,
                {
                    "title": "<p>New title</p>",
                    "read_at": "2024-11-24 18:00:00Z",
                    "reading_time": 10,
                },
                content_type="application/json",
            )

        self.article.refresh_from_db()
        assert self.article.title == "New title"
        assert self.article.read_at == utcdt(2024, 11, 24, 18)
        assert self.article.reading_time == 10
        snapshot.assert_match(
            serialize_for_snapshot(
                _prepare_article_for_serialization(response.json(), self.article)
            ),
            "article.json",
        )

    def test_update_tags(self, logged_in_sync_client, user, django_assert_num_queries, snapshot):
        existing_tag = TagFactory(user=user, title="Tag to keep")
        tag_to_delete = TagFactory(user=user, title="Tag to delete")
        self.article.tags.add(existing_tag, tag_to_delete)

        with django_assert_num_queries(17):
            response = logged_in_sync_client.patch(
                self.url,
                {
                    "tags": [existing_tag.slug, "", "<p>New tag</p>"],
                },
                content_type="application/json",
            )

        self.article.refresh_from_db()
        assert list(
            self.article.article_tags.all().values_list("tag__title", "tagging_reason")
        ) == [
            ("New tag", constants.TaggingReason.ADDED_MANUALLY),
            ("Tag to delete", constants.TaggingReason.DELETED),
            ("Tag to keep", constants.TaggingReason.ADDED_MANUALLY),
        ]
        snapshot.assert_match(
            serialize_for_snapshot(
                _prepare_article_for_serialization(response.json(), self.article)
            ),
            "article.json",
        )


@pytest.mark.django_db
class TestDeleteArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.url = reverse("api-1.0.0:delete_article", kwargs={"article_id": self.article.id})

    def test_not_logged_in(self, client):
        response = client.delete(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Article.objects.count() == 1

    def test_delete_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Article.objects.count() == 1

    def test_delete(self, logged_in_sync_client):
        response = logged_in_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Article.objects.count() == 0


@pytest.mark.django_db
class TestListTagsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag = TagFactory(
            user=user,
            title="Some tag",
        )
        self.url = reverse("api-1.0.0:list_tags")

    def test_not_logged_in(self, client):
        response = client.get(self.url, {}, content_type="application/json")

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_list(
        self, user, other_user, logged_in_sync_client, django_assert_num_queries, snapshot
    ):
        TagFactory(user=other_user, title="Some tag")
        tag_with_sub_tag = TagFactory(user=user, title="With sub tags")
        tag_with_sub_tag.sub_tags.add(self.tag)

        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        snapshot.assert_match(serialize_for_snapshot(response.json()), "tags.json")
