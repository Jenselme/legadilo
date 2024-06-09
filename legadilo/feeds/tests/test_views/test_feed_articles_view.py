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
from django.core.paginator import Paginator
from django.urls import reverse

from legadilo.feeds.models import FeedArticle
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.reading import constants as reading_constants
from legadilo.reading.tests.factories import ArticleFactory


@pytest.mark.django_db()
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

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_article_not_found(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_articles_of_feed(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/list_of_articles.html"
        assert response.context["page_title"] == f"Articles of feed '{self.feed.title}'"
        assert response.context["displayed_reading_list_id"] is None
        assert response.context["js_cfg"] == {}
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [self.article]
        assert response.context["update_articles_form"] is not None

    def test_only_article_update_action(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(
                self.url, {"update_action": reading_constants.UpdateArticleActions.MARK_AS_READ}
            )

        assert response.status_code == HTTPStatus.OK
