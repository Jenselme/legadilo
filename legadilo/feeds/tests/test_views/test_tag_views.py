from http import HTTPStatus

import pytest
from django.core.paginator import Paginator
from django.urls import reverse

from legadilo.feeds.models import ArticleTag
from legadilo.feeds.tests.factories import ArticleFactory, TagFactory


@pytest.mark.django_db()
class TestTagWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag_to_display = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        self.url = reverse("feeds:tag_with_articles", kwargs={"tag_slug": self.tag_to_display.slug})
        self.article_in_list = ArticleFactory(feed__user=user)
        ArticleTag.objects.create(tag=self.tag_to_display, article=self.article_in_list)
        other_article = ArticleFactory(feed__user=user)
        ArticleTag.objects.create(tag=other_tag, article=other_article)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_access_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_tag_with_articles_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["displayed_tag"] == self.tag_to_display
        assert response.context["reading_lists"] == []
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.article_in_list,
        ]
