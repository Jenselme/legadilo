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

import pytest
import time_machine
from django.core.management import call_command

from legadilo.feeds.models import FeedUpdate
from legadilo.feeds.tests.factories import FeedFactory, FeedUpdateFactory
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
        feed_keep_article_forever.articles.add(article_linked_to_forever_feed)
        feed_to_cleanup = FeedFactory(user=user, article_retention_time=1)
        article_linked_to_feed_to_cleanup = ArticleFactory(user=user, read_at=utcdt(2024, 6, 1))
        feed_to_cleanup.articles.add(article_linked_to_feed_to_cleanup)
        unread_article_linked_to_feed_to_cleanup = ArticleFactory(user=user)
        feed_to_cleanup.articles.add(unread_article_linked_to_feed_to_cleanup)

        with time_machine.travel("2024-07-01 00:00:00"):
            call_command("clean_data")

        assert list(Article.objects.all()) == [
            manually_added_feed,
            article_linked_to_forever_feed,
            unread_article_linked_to_feed_to_cleanup,
        ]
