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
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory


@pytest.mark.django_db()
class TestUpdateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.article = ArticleFactory(read_at=None, user=user)
        self.other_article = ArticleFactory(read_at=None, user=user)
        self.mark_as_read_url = reverse(
            "reading:update_article",
            kwargs={
                "article_id": self.article.id,
                "update_action": constants.UpdateArticleActions.MARK_AS_READ.name,
            },
        )
        self.mark_as_favorite_url = reverse(
            "reading:update_article",
            kwargs={
                "article_id": self.article.id,
                "update_action": constants.UpdateArticleActions.MARK_AS_FAVORITE.name,
            },
        )

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.mark_as_read_url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_update_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.mark_as_read_url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_article_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(
                self.mark_as_read_url, HTTP_REFERER="http://testserver/reading/"
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response.headers["Location"] == "http://testserver/reading/"
        self.article.refresh_from_db()
        self.other_article.refresh_from_db()
        assert self.article.is_read
        assert not self.other_article.is_read

    def test_update_article_view_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"displayed_reading_list_id": str(self.reading_list.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/update_article_action.html"
        assert response.context["article"] == self.article
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_unread_articles_of_reading_lists"] == {
            self.reading_list.slug: 1
        }
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": False,
            "auto_refresh_interval": 0,
            "articles_list_min_refresh_timeout": 300,
        }
        assert response["HX-Reswap"] == "innerHTML show:none"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        self.article.refresh_from_db()
        assert self.article.is_read
        assert b"<article" in response.content

    def test_update_article_view_with_htmx_mark_for_later_reading_list_dont_include_for_later(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        reading_list_hide_for_later = ReadingListFactory(
            user=user, for_later_status=constants.ForLaterStatus.ONLY_NOT_FOR_LATER
        )

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                reverse(
                    "reading:update_article",
                    kwargs={
                        "article_id": self.article.id,
                        "update_action": constants.UpdateArticleActions.MARK_AS_FOR_LATER.name,
                    },
                ),
                data={"displayed_reading_list_id": str(reading_list_hide_for_later.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/update_article_action.html"
        assert response.context["article"] == self.article
        assert response.context["delete_article_card"]
        assert response["HX-Reswap"] == "outerHTML show:none swap:1s"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        self.article.refresh_from_db()
        assert self.article.is_for_later
        assert b"<article" not in response.content

    def test_update_article_view_with_htmx_mark_not_for_later_reading_list_include_only_for_later(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        reading_list_hide_for_later = ReadingListFactory(
            user=user, for_later_status=constants.ForLaterStatus.ONLY_FOR_LATER
        )

        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                reverse(
                    "reading:update_article",
                    kwargs={
                        "article_id": self.article.id,
                        "update_action": constants.UpdateArticleActions.UNMARK_AS_FOR_LATER.name,
                    },
                ),
                data={"displayed_reading_list_id": str(reading_list_hide_for_later.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/update_article_action.html"
        assert response.context["article"] == self.article
        assert response.context["delete_article_card"]
        assert response["HX-Reswap"] == "outerHTML show:none swap:1s"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        self.article.refresh_from_db()
        assert not self.article.is_for_later
        assert b"<article" not in response.content

    def test_update_article_view_with_htmx_mark_for_later_reading_list_include_all(
        self, user, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                reverse(
                    "reading:update_article",
                    kwargs={
                        "article_id": self.article.id,
                        "update_action": constants.UpdateArticleActions.MARK_AS_FOR_LATER.name,
                    },
                ),
                data={"displayed_reading_list_id": str(self.reading_list.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/update_article_action.html"
        assert response.context["article"] == self.article
        assert not response.context["delete_article_card"]
        assert response["HX-Reswap"] == "innerHTML show:none"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        self.article.refresh_from_db()
        assert self.article.is_for_later
        assert b"<article" in response.content

    def test_update_article_view_for_article_details_read_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://example.com/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        location_url = reverse("reading:default_reading_list")
        assert response["Location"] == f"{location_url}?full_reload=true"

    def test_update_article_view_for_article_details_favorite_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(
                self.mark_as_favorite_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://testserver/reading/articles/1",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "http://testserver/reading/articles/1"


@pytest.mark.django_db()
class TestDeleteArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.reading_list_url = reverse(
            "reading:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "reading:delete_article",
            kwargs={
                "article_id": self.article.id,
            },
        )

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_delete_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:default_reading_list")
        assert Article.objects.count() == 0

    def test_delete_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(self.url, {"from_url": self.reading_list_url})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == self.reading_list_url
        assert Article.objects.count() == 0

    def test_delete_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(13):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "from_url": self.reading_list_url,
                    "displayed_reading_list_id": str(self.reading_list.id),
                },
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.context["article"].pk is None
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_unread_articles_of_reading_lists"] == {
            self.reading_list.slug: 0
        }
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
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
        with django_assert_num_queries(7):
            response = logged_in_sync_client.post(
                self.url, {"from_url": self.reading_list_url, "for_article_details": "True"}
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"{self.reading_list_url}?full_reload=true"
        assert Article.objects.count() == 0
