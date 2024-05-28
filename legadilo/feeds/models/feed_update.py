from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from django.db import models

from legadilo.feeds.constants import FEED_ERRORS_TIME_WINDOW

from .. import constants

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from .feed import Feed
else:
    TypedModelMeta = object


class FeedUpdateQuerySet(models.QuerySet["FeedUpdate"]):
    def for_feed(self, feed: Feed):
        return self.filter(feed=feed)

    def only_success(self):
        return self.filter(status=constants.FeedUpdateStatus.SUCCESS)

    def only_latest(self):
        return self.values("id").order_by("feed_id", "-created_at").distinct("feed_id")


class FeedUpdateManager(models.Manager["FeedUpdate"]):
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
                nb_errors=models.Count(
                    "id", filter=models.Q(status=constants.FeedUpdateStatus.FAILURE)
                ),
                nb_success=models.Count(
                    "id", filter=models.Q(status=constants.FeedUpdateStatus.SUCCESS)
                ),
            )
        )

        return aggregation["nb_errors"] > 0 and aggregation["nb_success"] == 0


class FeedUpdate(models.Model):
    status = models.CharField(choices=constants.FeedUpdateStatus.choices, max_length=100)
    error_message = models.TextField(blank=True)
    technical_debug_data = models.JSONField(blank=True, null=True)
    feed_etag = models.CharField(max_length=100)
    feed_last_modified = models.DateTimeField(null=True, blank=True)

    feed = models.ForeignKey("feeds.Feed", on_delete=models.CASCADE, related_name="feed_updates")

    created_at = models.DateTimeField(auto_now_add=True)

    objects = FeedUpdateManager()

    class Meta(TypedModelMeta):
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_status_valid",
                check=models.Q(status__in=constants.FeedUpdateStatus.names),
            )
        ]

    def __str__(self):
        return (
            f"FeedUpdate(feed__title={self.feed.title}, status={self.status}, "
            f"created_at={self.created_at})"
        )
