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

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models.functions import Coalesce

from legadilo.reading.models import Article

if TYPE_CHECKING:
    from .feed import Feed


class FeedDeletedArticleQuerySet(models.QuerySet["FeedDeletedArticle"]):
    pass


class FeedDeletedArticleManager(models.Manager["FeedDeletedArticle"]):
    def list_deleted_for_feed(self, feed: Feed) -> set[str]:
        deleted_links = (
            self.get_queryset()
            .filter(feed=feed)
            .aggregate(deleted=Coalesce(ArrayAgg("article_link"), []))
        )
        return set(deleted_links["deleted"])

    def delete_article(self, article: Article):
        feed_deleted_articles = []

        feed_articles_qs = article.feed_articles.all()
        for feed_article in feed_articles_qs:
            feed_deleted_articles.append(
                self.model(article_link=article.link, feed=feed_article.feed)
            )

        feed_articles_qs.delete()
        self.bulk_create(feed_deleted_articles, unique_fields=["article_link", "feed"])

        article.delete()

    def cleanup_articles(self):
        articles_qs = Article.objects.get_queryset().for_cleanup()

        for article in articles_qs:
            self.delete_article(article)

        return articles_qs.delete()


class FeedDeletedArticle(models.Model):
    article_link = models.URLField(max_length=1_024)

    created_at = models.DateTimeField(auto_now_add=True)

    feed = models.ForeignKey(
        "feeds.Feed", related_name="deleted_articles", on_delete=models.CASCADE
    )

    objects = FeedDeletedArticleManager()

    class Meta:
        db_table_comment = (
            "Maintain a list of deleted article links from a feed "
            "so we don't add it again on next update."
        )
        constraints = [
            models.UniqueConstraint(
                "article_link",
                "feed",
                name="%(app_label)s_%(class)s_delete_article_once_per_feed",
            )
        ]

    def __str__(self):
        return f"FeedDeletedArticle(article_link={self.article_link})"
