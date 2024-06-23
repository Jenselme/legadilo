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
        return list(
            self.get_queryset()
            .select_related("tag")
            .annotate(slug=models.F("tag__slug"))
            .values_list("slug", flat=True)
        )

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
