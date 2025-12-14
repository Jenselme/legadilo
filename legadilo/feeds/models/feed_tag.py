# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models

from legadilo.reading.models.tag import Tag

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from .feed import Feed
else:
    TypedModelMeta = object


class FeedTagQuerySet(models.QuerySet["FeedTag"]):
    pass


class FeedTagManager(models.Manager["FeedTag"]):
    _hints: dict

    def get_queryset(self) -> FeedTagQuerySet:
        return FeedTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_selected_values(self) -> list[str]:
        return list(self.get_queryset().values_list("tag__slug", flat=True))

    def associate_feed_with_tags(self, feed: Feed, tags: Iterable[Tag]):
        feed_tags = [self.model(feed=feed, tag=tag) for tag in tags]
        self.bulk_create(feed_tags, ignore_conflicts=True, unique_fields=["feed_id", "tag_id"])

    def associate_feed_with_tag_slugs(
        self, feed: Feed, tag_slugs: list[str], *, clear_existing=False
    ):
        if clear_existing:
            feed.feed_tags.all().delete()
        self.associate_feed_with_tags(
            feed, Tag.objects.get_or_create_from_list(feed.user, tag_slugs)
        )


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
