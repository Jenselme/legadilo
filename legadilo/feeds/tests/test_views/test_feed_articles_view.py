# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.core.paginator import Paginator
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.feeds.models import FeedArticle
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.reading import constants as reading_constants
from legadilo.reading.tests.factories import ArticleFactory


@pytest.mark.django_db
class TestFeedArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed = FeedFactory(user=user)
        self.article = ArticleFactory(user=user)
        FeedArticle.objects.create(feed=self.feed, article=self.article)
        self.url = reverse(
            "feeds:feed_articles", kwargs={"feed_id": self.feed.id, "feed_slug": self.feed.slug}
        )
        self.url_no_slug = reverse("feeds:feed_articles", kwargs={"feed_id": self.feed.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_article_not_found(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_articles_of_feed(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/list_of_articles.html"
        assert response.context_data["page_title"] == f"Articles of feed '{self.feed.title}'"
        assert response.context_data["displayed_reading_list"] is None
        assert response.context_data["js_cfg"] == {}
        assert isinstance(response.context_data["articles_paginator"], Paginator)
        assert response.context_data["articles_page"].object_list == [self.article]
        assert response.context_data["update_articles_form"] is not None

    def test_only_article_update_action(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(15):
            response = logged_in_sync_client.post(
                self.url, {"update_action": reading_constants.UpdateArticleActions.MARK_AS_READ}
            )

        assert response.status_code == HTTPStatus.OK
