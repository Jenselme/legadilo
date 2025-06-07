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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

from dateutil.relativedelta import relativedelta
from django.db import models

from ...utils.time_utils import utcnow
from ...utils.validators import list_of_strings_validator
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

    def for_cleanup(self, latest_feed_update_ids: set[int | None]):
        return self.filter(
            created_at__lt=utcnow() - relativedelta(days=constants.KEEP_FEED_UPDATES_FOR)
        ).exclude(id__in=latest_feed_update_ids)


class FeedUpdateManager(models.Manager["FeedUpdate"]):
    _hints: dict

    def get_queryset(self) -> FeedUpdateQuerySet:
        return FeedUpdateQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_latest_success_for_feed_id(self, feed_id: int):
        return self.get_queryset().filter(feed_id=feed_id).only_success().first()

    def must_disable_feed(
        self,
        feed: Feed,
    ) -> bool:
        time_window = self._get_feed_deactivation_error_time_window(feed)
        aggregation = (
            self.get_queryset()
            .for_feed(feed)
            .filter(created_at__gt=utcnow() - time_window)
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

    def _get_feed_deactivation_error_time_window(self, feed: Feed) -> relativedelta:
        # The idea is to find a compromise to not keep trying to update a feed that's broken and is
        # likely to stay broken and the frequency of updates. We give longer times to feeds that we
        # don't fetch often and less for others.
        refresh_delay: constants.FeedRefreshDelays = constants.FeedRefreshDelays(feed.refresh_delay)
        match refresh_delay:
            case constants.FeedRefreshDelays.HOURLY | constants.FeedRefreshDelays.BIHOURLY:
                return relativedelta(weeks=2)
            case (
                constants.FeedRefreshDelays.EVERY_MORNING
                | constants.FeedRefreshDelays.DAILY_AT_NOON
                | constants.FeedRefreshDelays.EVERY_EVENING
            ):
                return relativedelta(weeks=2)
            case (
                constants.FeedRefreshDelays.ON_MONDAYS
                | constants.FeedRefreshDelays.ON_THURSDAYS
                | constants.FeedRefreshDelays.ON_SATURDAYS
                | constants.FeedRefreshDelays.ON_SUNDAYS
                | constants.FeedRefreshDelays.TWICE_A_WEEK
            ):
                return relativedelta(months=2)
            case (
                constants.FeedRefreshDelays.FIRST_DAY_OF_THE_MONTH
                | constants.FeedRefreshDelays.MIDDLE_OF_THE_MONTH
                | constants.FeedRefreshDelays.END_OF_THE_MONTH
                | constants.FeedRefreshDelays.THRICE_A_MONTH
            ):
                return relativedelta(months=4)
            case _:
                assert_never(refresh_delay)


class FeedUpdate(models.Model):
    status = models.CharField(choices=constants.FeedUpdateStatus.choices, max_length=100)  # type: ignore[misc]
    ignored_article_urls = models.JSONField(
        validators=[list_of_strings_validator], blank=True, default=list
    )
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
                condition=models.Q(status__in=constants.FeedUpdateStatus.names),
            )
        ]

    def __str__(self):
        return (
            f"FeedUpdate(feed__title={self.feed.title}, status={self.status}, "
            f"created_at={self.created_at})"
        )
