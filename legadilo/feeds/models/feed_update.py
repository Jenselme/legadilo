from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from django.db import models

from legadilo.feeds.constants import FEED_ERRORS_TIME_WINDOW

if TYPE_CHECKING:
    from .feed import Feed


class FeedUpdateQuerySet(models.QuerySet):
    def for_feed(self, feed: Feed):
        return self.filter(feed=feed)

    def only_success(self):
        return self.filter(success=True)


class FeedUpdateManager(models.Manager):
    _hints: dict

    def get_queryset(self) -> FeedUpdateQuerySet:
        return FeedUpdateQuerySet(model=self.model, using=self._db, hints=self._hints)

    async def get_latest_success_for_feed(self, feed: Feed):
        return await self.get_queryset().for_feed(feed).only_success().afirst()

    def must_disable_feed(
        self,
        feed: Feed,
    ) -> bool:
        aggregation = (
            self.get_queryset()
            .for_feed(feed)
            .filter(created_at__gt=datetime.now(UTC) - FEED_ERRORS_TIME_WINDOW)
            .aggregate(
                nb_errors=models.Count("id", filter=models.Q(success=False)),
                nb_success=models.Count("id", filter=models.Q(success=True)),
            )
        )

        return aggregation["nb_errors"] > 0 and aggregation["nb_success"] == 0


class FeedUpdate(models.Model):
    success = models.BooleanField()
    error_message = models.TextField(blank=True)
    feed_etag = models.CharField()
    feed_last_modified = models.DateTimeField(null=True, blank=True)

    feed = models.ForeignKey("feeds.Feed", on_delete=models.CASCADE, related_name="feed_updates")

    created_at = models.DateTimeField(auto_now_add=True)

    objects = FeedUpdateManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"FeedUpdate(feed__title={self.feed.title}, success={self.success}, created_at={self.created_at})"
