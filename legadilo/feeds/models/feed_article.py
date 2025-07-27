# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import TYPE_CHECKING

from django.db import models

from legadilo.utils.time_utils import utcnow

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class FeedArticleManager(models.Manager):
    pass


class FeedArticle(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_articles", on_delete=models.CASCADE)
    article = models.ForeignKey(
        "reading.Article", related_name="feed_articles", on_delete=models.PROTECT
    )

    feed_article_id = models.TextField()
    last_seen_at = models.DateTimeField(default=utcnow)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FeedArticleManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "article", name="%(app_label)s_%(class)s_article_linked_once_per_feed"
            ),
            # To speed up the search by feed_article_id
            models.UniqueConstraint(
                "feed",
                "feed_article_id",
                name="%(app_label)s_%(class)s_article_linked_once_per_feed_id",
            ),
        ]

    def __str__(self):
        return f"FeedArticle(feed={self.feed}, article={self.article})"
