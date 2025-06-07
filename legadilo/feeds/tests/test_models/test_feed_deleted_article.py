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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import time_machine

from legadilo.feeds.models import FeedArticle, FeedDeletedArticle
from legadilo.feeds.tests.factories import FeedDeletedArticleFactory, FeedFactory
from legadilo.reading import constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestFeedDeletedArticleManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        pass

    def test_list_deleted_for_feed(self):
        feed = FeedFactory()
        deleted1 = FeedDeletedArticleFactory(feed=feed)
        deleted2 = FeedDeletedArticleFactory(feed=feed)
        FeedDeletedArticleFactory()

        all_deleted = FeedDeletedArticle.objects.list_deleted_for_feed(feed)

        assert all_deleted == {deleted1.article_url, deleted2.article_url}

    def test_list_deleted_for_feed_nothing_deleted(self):
        feed = FeedFactory()

        all_deleted = FeedDeletedArticle.objects.list_deleted_for_feed(feed)

        assert list(all_deleted) == []

    def test_delete_article_not_linked_to_feed(self):
        article = ArticleFactory()

        FeedDeletedArticle.objects.delete_article(article)

        assert Article.objects.count() == 0
        assert FeedDeletedArticle.objects.count() == 0

    def test_delete_article_linked_to_feeds(self, user):
        article = ArticleFactory(user=user)
        feed1 = FeedFactory(user=user)
        FeedArticle.objects.create(article=article, feed=feed1)
        feed2 = FeedFactory(user=user)
        FeedArticle.objects.create(article=article, feed=feed2)

        FeedDeletedArticle.objects.delete_article(article)

        assert Article.objects.count() == 0
        assert FeedDeletedArticle.objects.count() == 2
        assert feed1.deleted_articles.count() == 1
        deleted_article = feed1.deleted_articles.get()
        assert deleted_article.article_url == article.url

    def test_cleanup_articles(self, user):
        ArticleFactory(
            title="Read not linked to a feed (to keep)",
            user=user,
            read_at=utcdt(2024, 6, 1),
            main_source_type=constants.ArticleSourceType.MANUAL,
        )
        read_keep_one_and_seven_days_retention_to_keep = ArticleFactory(
            title="Read keep 1 and 7 days (to keep)",
            user=user,
            read_at=utcdt(2024, 6, 1),
            main_source_type=constants.ArticleSourceType.FEED,
        )
        feed_forever_retention = FeedFactory(user=user, article_retention_time=0)
        feed_forever_retention.articles.add(read_keep_one_and_seven_days_retention_to_keep)
        read_1_day_retention_to_cleanup = ArticleFactory(
            title="Read, 1 day retention (to cleanup)",
            user=user,
            read_at=utcdt(2024, 6, 1),
            main_source_type=constants.ArticleSourceType.FEED,
        )
        feed_one_day_retention = FeedFactory(user=user, article_retention_time=1)
        feed_one_day_retention.articles.add(read_1_day_retention_to_cleanup)

        with time_machine.travel("2024-06-07 00:00:00"):
            deletion_result = FeedDeletedArticle.objects.cleanup_articles()

        assert deletion_result == (1, {"reading.Article": 1})
        assert list(FeedDeletedArticle.objects.all().values_list("article_url", flat=True)) == [
            read_1_day_retention_to_cleanup.url
        ]
        assert Article.objects.count() == 2
