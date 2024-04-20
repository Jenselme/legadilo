from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.tests.factories import ArticleFactory, ReadingListFactory


@pytest.mark.django_db()
class TestArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "feeds:article_details",
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
            "feeds:article_details",
            kwargs={"article_id": self.article.id, "article_slug": "toto"},
        )

        response = logged_in_sync_client.get(url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_view_details(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(4):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["article"] == self.article
        assert response.context["from_url"] == reverse("feeds:default_reading_list")

    def test_view_details_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        from_url = "/reading/lists/unread/"
        with django_assert_num_queries(4):
            response = logged_in_sync_client.get(self.url, data={"from_url": from_url})

        assert response.status_code == HTTPStatus.OK
        assert response.context["article"] == self.article
        assert response.context["from_url"] == from_url


@pytest.mark.django_db()
class TestUpdateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.article = ArticleFactory(is_read=False, user=user)
        self.mark_as_read_url = reverse(
            "feeds:update_article",
            kwargs={
                "article_id": self.article.id,
                "update_action": constants.UpdateArticleActions.MARK_AS_READ.name,
            },
        )
        self.mark_as_favorite_url = reverse(
            "feeds:update_article",
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
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_read_url, HTTP_REFERER="http://testserver/reading/"
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response.headers["Location"] == "http://testserver/reading/"
        self.article.refresh_from_db()
        assert self.article.is_read

    def test_update_article_view_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"displayed_reading_list_id": str(self.reading_list.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.context["article"] == self.article
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_articles_of_reading_lists"] == {self.reading_list.slug: 1}
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": False,
            "auto_refresh_interval": 0,
            "articles_list_min_refresh_timeout": 300,
        }
        self.article.refresh_from_db()
        assert self.article.is_read

    def test_update_article_view_for_article_details_read_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://example.com/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:default_reading_list")

    def test_update_article_view_for_article_details_favorite_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_favorite_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://testserver/reading/articles/1",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "http://testserver/reading/articles/1"
