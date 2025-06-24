# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models.functions import Coalesce

from legadilo.reading.models import Article
from legadilo.types import DeletionResult

from ...utils.collections_utils import merge_deletion_results

if TYPE_CHECKING:
    from .feed import Feed


class FeedDeletedArticleQuerySet(models.QuerySet["FeedDeletedArticle"]):
    pass


class FeedDeletedArticleManager(models.Manager["FeedDeletedArticle"]):
    def list_deleted_for_feed(self, feed: Feed) -> set[str]:
        deleted_urls = (
            self.get_queryset()
            .filter(feed=feed)
            .aggregate(deleted=Coalesce(ArrayAgg("article_url"), []))
        )
        return set(deleted_urls["deleted"])

    def delete_article(self, article: Article):
        feed_deleted_articles = []

        feed_articles_qs = article.feed_articles.all()
        for feed_article in feed_articles_qs:
            feed_deleted_articles.append(
                self.model(article_url=article.url, feed=feed_article.feed)
            )

        feed_articles_qs.delete()
        self.bulk_create(feed_deleted_articles, unique_fields=["article_url", "feed"])

        return article.delete()

    def cleanup_articles(self) -> DeletionResult:
        articles_qs = Article.objects.get_queryset().for_cleanup()
        deletion_results = []

        for article in articles_qs:
            deletion_results.append(self.delete_article(article))

        return merge_deletion_results(deletion_results)


class FeedDeletedArticle(models.Model):
    article_url = models.URLField(max_length=1_024)

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
                "article_url",
                "feed",
                name="%(app_label)s_%(class)s_delete_article_once_per_feed",
            )
        ]

    def __str__(self):
        return f"FeedDeletedArticle(article_url={self.article_url})"
