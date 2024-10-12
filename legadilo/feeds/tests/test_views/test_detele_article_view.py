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
from legadilo.feeds.models import FeedArticle, FeedDeletedArticle
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory


@pytest.mark.django_db
class TestDeleteArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.reading_list_url = reverse(
            "reading:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "feeds:delete_article",
            kwargs={
                "article_id": self.article.id,
            },
        )

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert_redirected_to_login_page(response)

    def test_cannot_delete_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:default_reading_list")
        assert Article.objects.count() == 0

    def test_delete_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(self.url, {"from_url": self.reading_list_url})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == self.reading_list_url
        assert Article.objects.count() == 0

    def test_delete_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(18):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "from_url": self.reading_list_url,
                    "displayed_reading_list_id": str(self.reading_list.id),
                },
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_unread_articles_of_reading_lists"] == {
            self.reading_list.slug: 0
        }
        assert response.context["displayed_reading_list"] == self.reading_list
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": False,
            "auto_refresh_interval": 0,
            "articles_list_min_refresh_timeout": 300,
        }
        assert response["HX-Reswap"] == "outerHTML show:none swap:1s"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        assert Article.objects.count() == 0
        assert b"<article" not in response.content

    def test_delete_article_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(12):
            response = logged_in_sync_client.post(
                self.url, {"from_url": self.reading_list_url, "for_article_details": "True"}
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"{self.reading_list_url}?full_reload=true"
        assert Article.objects.count() == 0

    def test_delete_article_linked_with_feed(
        self, logged_in_sync_client, django_assert_num_queries, user
    ):
        feed = FeedFactory(user=user)
        FeedArticle.objects.create(feed=feed, article=self.article)

        with django_assert_num_queries(14):
            response = logged_in_sync_client.post(
                self.url, {"from_url": self.reading_list_url, "for_article_details": "True"}
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"{self.reading_list_url}?full_reload=true"
        assert Article.objects.count() == 0
        assert FeedArticle.objects.count() == 0
        assert FeedDeletedArticle.objects.count() == 1
        feed_deleted_article = FeedDeletedArticle.objects.get()
        assert feed_deleted_article.feed == feed
        assert feed_deleted_article.article_link == self.article.link
