# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import time_machine
from django.core.management import call_command

from legadilo.feeds.models import FeedUpdate
from legadilo.feeds.tests.factories import FeedArticleFactory, FeedFactory, FeedUpdateFactory
from legadilo.reading.models import Article, ArticleFetchError
from legadilo.reading.tests.factories import ArticleFactory, ArticleFetchErrorFactory
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestCleanDataCommand:
    def test_clean_data_no_objects(self):
        call_command("clean_data")

    def test_clean_old_feed_updates(self):
        feed = FeedFactory()
        with time_machine.travel("2024-03-15 12:00:00"):
            FeedUpdateFactory(feed=feed)

        with time_machine.travel("2024-05-01 12:00:00"):
            feed_update_to_keep = FeedUpdateFactory(feed=feed)

        with time_machine.travel("2024-06-01 12:00:00"):
            call_command("clean_data")

        assert list(FeedUpdate.objects.all()) == [feed_update_to_keep]

    def test_clean_old_fetch_errors(self):
        with time_machine.travel("2024-03-15 12:00:00"):
            ArticleFetchErrorFactory()
        with time_machine.travel("2024-05-01 12:00:00"):
            object_to_keep = ArticleFetchErrorFactory()

        with time_machine.travel("2024-06-01 12:00:00"):
            call_command("clean_data")

        assert list(ArticleFetchError.objects.all()) == [object_to_keep]

    def test_clean_old_feed_articles(self, user):
        manually_added_feed = ArticleFactory(title="Manually added", read_at=utcdt(2024, 6, 1))
        feed_keep_article_forever = FeedFactory(user=user, article_retention_time=0)
        article_linked_to_forever_feed = ArticleFactory(
            title="Manually added", user=user, read_at=utcdt(2024, 6, 1)
        )
        feed_article_to_keep = FeedArticleFactory(
            feed=feed_keep_article_forever, article=article_linked_to_forever_feed
        )
        feed_to_cleanup = FeedFactory(user=user, article_retention_time=1)
        article_linked_to_feed_to_cleanup = ArticleFactory(user=user, read_at=utcdt(2024, 6, 1))
        feed_article_to_cleanup = FeedArticleFactory(
            feed=feed_to_cleanup, article=article_linked_to_feed_to_cleanup
        )
        unread_article_linked_to_feed_to_cleanup = ArticleFactory(user=user)
        feed_article_unread = FeedArticleFactory(
            feed=feed_to_cleanup, article=unread_article_linked_to_feed_to_cleanup
        )

        with time_machine.travel("2024-07-01 00:00:00"):
            call_command("clean_data")

        assert list(Article.objects.all()) == [
            manually_added_feed,
            article_linked_to_forever_feed,
            unread_article_linked_to_feed_to_cleanup,
        ]
        feed_article_to_keep.refresh_from_db()
        assert feed_article_to_keep.article == article_linked_to_forever_feed
        feed_article_to_cleanup.refresh_from_db()
        assert feed_article_to_cleanup.article is None
        feed_article_unread.refresh_from_db()
        assert feed_article_unread.article == unread_article_linked_to_feed_to_cleanup
