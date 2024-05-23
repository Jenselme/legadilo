from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.reading.models.tag import Tag

    from .feed import Feed
else:
    TypedModelMeta = object


class FeedTagQuerySet(models.QuerySet["FeedTag"]):
    pass


class FeedTagManager(models.Manager["FeedTag"]):
    _hints: dict

    def get_queryset(self) -> FeedTagQuerySet:
        return FeedTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def associate_feed_with_tags(self, feed: Feed, tags: Iterable[Tag]):
        feed_tags = [self.model(feed=feed, tag=tag) for tag in tags]
        self.bulk_create(feed_tags, ignore_conflicts=True, unique_fields=["feed_id", "tag_id"])


class FeedTag(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_tags", on_delete=models.CASCADE)
    tag = models.ForeignKey("reading.Tag", related_name="feed_tags", on_delete=models.CASCADE)

    objects = FeedTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "tag", name="%(app_label)s_%(class)s_tagged_once_per_feed"
            )
        ]
        ordering = ["tag__title", "tag_id"]

    def __str__(self):
        return f"FeedTag(feed={self.feed}, tag={self.tag})"
