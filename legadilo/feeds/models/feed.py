from __future__ import annotations

import calendar
from datetime import timedelta
from typing import TYPE_CHECKING, assert_never

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from legadilo.reading import constants as reading_constants
from legadilo.reading.models.article import Article
from legadilo.reading.models.tag import Tag
from legadilo.users.models import User

from ...utils.time import utcnow
from .. import constants as feeds_constants
from ..utils.feed_parsing import FeedData
from .feed_article import FeedArticle
from .feed_tag import FeedTag
from .feed_update import FeedUpdate

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from .feed_category import FeedCategory
else:
    TypedModelMeta = object


def _build_refresh_filters(refresh_delay: feeds_constants.FeedRefreshDelays) -> models.When:  # noqa: C901, PLR0911 too complex
    now = utcnow()
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    base_filters = models.Q(refresh_delay=refresh_delay)

    # Notes: cron will run each hour. Since it will take time to complete, we use 45m instead
    # in 1h in our tests.
    match refresh_delay:
        case feeds_constants.FeedRefreshDelays.HOURLY:
            return models.When(
                base_filters
                & models.Q(latest_feed_update__created_at__lte=now - timedelta(minutes=45)),
                then=True,
            )
        case feeds_constants.FeedRefreshDelays.BIHOURLY:
            return models.When(
                base_filters
                & models.Q(
                    latest_feed_update__created_at__lte=now - timedelta(hours=1, minutes=45)
                ),
                then=True,
            )
        case feeds_constants.FeedRefreshDelays.EVERY_MORNING:
            if 8 <= now.hour <= 12:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.DAILY_AT_NOON:
            if 11 <= now.hour <= 13:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.EVERY_EVENING:
            if 20 <= now.hour <= 22:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_MONDAYS:
            if now.weekday() == calendar.MONDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_THURSDAYS:
            if now.weekday() == calendar.THURSDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.TWICE_A_WEEK:
            if now.weekday() in {calendar.MONDAY, calendar.THURSDAY}:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.FIRST_DAY_OF_THE_MONTH:
            if now.day == 1:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.MIDDLE_OF_THE_MONTH:
            if now.day == 15:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.END_OF_THE_MONTH:
            if now.day == last_day_of_month:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.THRICE_A_MONTH:
            if now.day in {1, 15, last_day_of_month}:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__day=now.day), then=True
                )
            return models.When(base_filters, then=False)
        case _:
            assert_never(refresh_delay)


class FeedQuerySet(models.QuerySet["Feed"]):
    def only_with_ids(self, feed_ids: list[int] | None = None):
        feeds_to_update = self
        if feed_ids:
            feeds_to_update = feeds_to_update.filter(id__in=feed_ids)

        return feeds_to_update

    def for_update(self):
        return self.alias(
            # We need to filter for update only on the latest FeedUpdate object. If we have entries
            # that are too old, we don't want to include them or the feed will be refreshed even if
            # according to its rules it should: by default, we do a left join of FeedUpdate thus
            # getting on the whole history. We only want to run our test on the latest entry to
            # check whether it's too old and thus must be updated or not.
            latest_feed_update=models.FilteredRelation(
                "feed_updates",
                condition=models.Q(
                    feed_updates__id__in=models.Subquery(
                        FeedUpdate.objects.get_queryset().only_latest()
                    )
                ),
            ),
            must_update=models.Case(
                *[
                    _build_refresh_filters(refresh_delay)
                    for refresh_delay in feeds_constants.FeedRefreshDelays
                ],
                default=False,
                output_field=models.BooleanField(),
            ),
        ).filter(must_update=True, enabled=True)


class FeedManager(models.Manager["Feed"]):
    _hints: dict

    def get_queryset(self) -> FeedQuerySet:
        return FeedQuerySet(model=self.model, using=self._db, hints=self._hints)

    @transaction.atomic()
    def create_from_metadata(
        self,
        feed_metadata: FeedData,
        user: User,
        refresh_delay: feeds_constants.FeedRefreshDelays,
        tags: list[Tag],
        category: FeedCategory | None = None,
    ) -> Feed:
        feed = self.create(
            feed_url=feed_metadata.feed_url,
            site_url=feed_metadata.site_url,
            title=feed_metadata.title[: feeds_constants.FEED_TITLE_MAX_LENGTH],
            refresh_delay=refresh_delay,
            description=feed_metadata.description,
            feed_type=feed_metadata.feed_type,
            category=category,
            user=user,
        )
        FeedTag.objects.associate_feed_with_tags(feed, tags)
        self.update_feed(feed, feed_metadata)
        return feed

    @transaction.atomic()
    def update_feed(self, feed: Feed, feed_metadata: FeedData):
        created_articles = Article.objects.update_or_create_from_articles_list(
            feed.user,
            feed_metadata.articles,
            feed.tags.all(),
            source_type=reading_constants.ArticleSourceType.FEED,
        )
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.SUCCESS,
            feed_etag=feed_metadata.etag,
            feed_last_modified=feed_metadata.last_modified,
            feed=feed,
        )
        FeedArticle.objects.bulk_create(
            [FeedArticle(article=article, feed=feed) for article in created_articles],
            ignore_conflicts=True,
        )

    @transaction.atomic()
    def log_error(self, feed: Feed, error_message: str):
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.FAILURE,
            error_message=error_message,
            feed=feed,
        )
        if FeedUpdate.objects.must_disable_feed(feed):
            feed.disable(_("We failed too many times to fetch the feed"))
            feed.save()

    def log_not_modified(self, feed: Feed):
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.NOT_MODIFIED,
            feed=feed,
        )


class Feed(models.Model):
    feed_url = models.URLField()
    site_url = models.URLField()
    enabled = models.BooleanField(default=True)
    disabled_reason = models.TextField(blank=True)

    # We store some feeds metadata, so we don't have to fetch when we need it.
    title = models.CharField(max_length=feeds_constants.FEED_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)
    feed_type = models.CharField(choices=feeds_constants.SupportedFeedType.choices, max_length=100)
    refresh_delay = models.CharField(
        choices=feeds_constants.FeedRefreshDelays.choices,
        max_length=100,
        default=feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
    )

    user = models.ForeignKey("users.User", related_name="feeds", on_delete=models.CASCADE)
    category = models.ForeignKey(
        "feeds.FeedCategory", related_name="feeds", on_delete=models.SET_NULL, null=True
    )
    articles = models.ManyToManyField(
        "reading.Article",
        related_name="feeds",
        through="feeds.FeedArticle",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = FeedManager()

    class Meta(TypedModelMeta):
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                "feed_url", "user", name="%(app_label)s_%(class)s_feed_url_unique"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_feed_type_valid",
                check=models.Q(
                    feed_type__in=feeds_constants.SupportedFeedType.names,
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_refresh_delay_type_valid",
                check=models.Q(
                    refresh_delay__in=feeds_constants.FeedRefreshDelays.names,
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_disabled_reason_empty_when_enabled",
                check=models.Q(
                    disabled_reason="",
                    enabled=True,
                )
                | models.Q(enabled=False),
            ),
        ]

    def __str__(self):
        category_name = self.category.name if self.category else "None"
        return f"Feed(title={self.title}, feed_type={self.feed_type}, category={category_name})"

    def disable(self, reason=""):
        self.disabled_reason = reason
        self.enabled = False
