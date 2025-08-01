# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, assert_never, cast
from zoneinfo import ZoneInfo

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from legadilo.reading import constants as reading_constants
from legadilo.reading.models.article import Article, ArticleQuerySet, SaveArticleResult
from legadilo.reading.models.tag import Tag
from legadilo.users.models import User
from legadilo.utils.types import DeletionResult

from ...users.models import Notification
from ...utils.time_utils import utcnow
from .. import constants as feeds_constants
from ..services.feed_parsing import FeedData
from .feed_article import FeedArticle
from .feed_tag import FeedTag
from .feed_update import FeedUpdate

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from .feed_category import FeedCategory
else:
    TypedModelMeta = object


def _build_refresh_filters(  # noqa: C901, PLR0911, PLR0912 too complex
    tzinfo: ZoneInfo, refresh_delay: feeds_constants.FeedRefreshDelays
) -> models.When:
    now = datetime.now(tzinfo)
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    base_filters = models.Q(refresh_delay=refresh_delay)

    # Notes: cron will run each hour. Since it will take time to complete, we use 45m instead
    # in 1h in our conditions.
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
            if 8 <= now.hour <= 10:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.DAILY_AT_NOON:
            if 12 <= now.hour <= 14:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.EVERY_EVENING:
            if 20 <= now.hour <= 22:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_MONDAYS:
            if now.weekday() == calendar.MONDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_THURSDAYS:
            if now.weekday() == calendar.THURSDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_SATURDAYS:
            if now.weekday() == calendar.SATURDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.ON_SUNDAYS:
            if now.weekday() == calendar.SUNDAY:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.TWICE_A_WEEK:
            if now.weekday() in {calendar.MONDAY, calendar.THURSDAY}:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.FIRST_DAY_OF_THE_MONTH:
            if now.day == 1:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.MIDDLE_OF_THE_MONTH:
            if now.day == 15:  # noqa: PLR2004 Magic value used in comparison
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.END_OF_THE_MONTH:
            if now.day == last_day_of_month:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case feeds_constants.FeedRefreshDelays.THRICE_A_MONTH:
            if now.day in {1, 15, last_day_of_month}:
                return models.When(
                    base_filters & ~models.Q(latest_feed_update__created_at__date=now.date()),
                    then=True,
                )
            return models.When(base_filters, then=False)
        case _:
            assert_never(refresh_delay)


class FeedQuerySet(models.QuerySet["Feed"]):
    def create(self, **kwargs):
        kwargs.setdefault("slug", slugify(kwargs["title"]))
        return super().create(**kwargs)

    def only_with_ids(self, feed_ids: list[int]):
        return self.filter(id__in=feed_ids)

    def only_enabled(self):
        return self.for_status_search(enabled=True)

    def for_update(self, user: User):
        return (
            self.alias(
                # We need to filter for update only on the latest FeedUpdate object. If we have
                # entries that are too old, we don't want to include them or the feed will be
                # refreshed even if according to its rules it should not: by default, we do a left
                # join of FeedUpdate thus getting on the whole history. We only want to run our test
                # on the latest entry to check whether it's too old and thus must be updated or not.
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
                        _build_refresh_filters(user.tzinfo, refresh_delay)
                        for refresh_delay in feeds_constants.FeedRefreshDelays
                    ],
                    default=False,
                    output_field=models.BooleanField(),
                ),
            )
            .only_enabled()
            .filter(must_update=True)
        )

    def for_user(self, user: User):
        return self.filter(user=user)

    def for_export(self, user: User, *, updated_since: datetime | None = None):
        qs = self.for_user(user).select_related("category").order_by("id")
        if updated_since:
            qs = qs.filter(updated_at__gte=updated_since)

        return qs

    def for_api(self):
        return self.select_related("category").prefetch_related("tags")

    def for_feed_urls_search(self, urls: list[str]):
        filters = models.Q()
        for url in urls:
            filters |= models.Q(feed_url=url)

        return self.filter(filters)

    def for_status_search(self, *, enabled: bool):
        return self.filter(enabled=enabled)


class FeedManager(models.Manager["Feed"]):
    _hints: dict

    def get_queryset(self) -> FeedQuerySet:
        return FeedQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_by_categories(
        self, user: User, searched_text: str = ""
    ) -> dict[str | None, list[Feed]]:
        feeds_by_categories: dict[str | None, list[Feed]] = {}
        qs = (
            self.get_queryset()
            .for_user(user)
            .select_related("category")
            .order_by("category__title", "id")
        )

        if searched_text:
            qs = qs.filter(title__icontains=searched_text)

        for feed in qs:
            category_title = feed.category.title if feed.category else None
            feeds_by_categories.setdefault(category_title, []).append(feed)

        return feeds_by_categories

    def get_articles(self, feed: Feed) -> ArticleQuerySet:
        return cast(ArticleQuerySet, feed.articles.all()).for_feed()

    def cleanup_feed_updates(self) -> DeletionResult:
        latest_feed_update_ids = (
            self.get_queryset()
            .alias(
                alias_feed_update_ids=ArrayAgg(
                    "feed_updates__id", ordering="-feed_updates__created_at"
                ),
            )
            .annotate(annot_latest_feed_update_id=models.F("alias_feed_update_ids__0"))
            .values_list("annot_latest_feed_update_id", flat=True)
        )
        return FeedUpdate.objects.get_queryset().for_cleanup(set(latest_feed_update_ids)).delete()

    @transaction.atomic()
    def create_from_metadata(  # noqa: PLR0913 too many arguments
        self,
        feed_data: FeedData,
        user: User,
        refresh_delay: feeds_constants.FeedRefreshDelays,
        article_retention_time: int,
        tags: list[Tag],
        category: FeedCategory | None = None,
        *,
        open_original_url_by_default=False,
    ) -> tuple[Feed, bool]:
        feed, created = self.get_or_create(
            user=user,
            feed_url=feed_data.feed_url,
            defaults={
                "site_url": feed_data.site_url,
                "title": feed_data.title,
                "refresh_delay": refresh_delay,
                "article_retention_time": article_retention_time,
                "open_original_url_by_default": open_original_url_by_default,
                "description": feed_data.description,
                "feed_type": feed_data.feed_type,
                "category": category,
            },
        )

        if created:
            FeedTag.objects.associate_feed_with_tags(feed, tags)
            self.update_feed(feed, feed_data)
        elif not feed.enabled:
            feed.enable()
            feed.save()
            self.update_feed(feed, feed_data)

        return feed, created

    @transaction.atomic()
    def update_feed(self, feed: Feed, feed_data: FeedData):
        self._update_article_urls_from_feed(feed, feed_data)
        deleted_feed_article_ids = FeedArticle.objects.list_deleted_feed_article_ids(feed.id)
        articles = [
            article
            for article in feed_data.articles
            if article.external_article_id not in deleted_feed_article_ids
        ]
        save_results = Article.objects.save_from_list_of_data(
            feed.user,
            articles,
            feed.tags.all(),
            source_type=reading_constants.ArticleSourceType.FEED,
        )
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.SUCCESS,
            ignored_article_ids=list(deleted_feed_article_ids),
            feed_etag=feed_data.etag,
            feed_last_modified=feed_data.last_modified,
            feed=feed,
        )
        self._mark_republished_articles_as_unread(feed, feed_data)
        self._delete_feed_article_linked_wrong_article(feed, save_results)
        FeedArticle.objects.bulk_create(
            [
                FeedArticle(
                    article=result.article,
                    feed=feed,
                    feed_article_id=result.article_id_in_data,
                    last_seen_at=utcnow(),
                )
                for result in save_results
            ],
            update_conflicts=True,
            # feed_article_id should be stable for a given feed. But if it changes and we can find
            # the article with its URL, update it here in case it changed.
            # last_seen_at must be updated no matter what.
            update_fields=["feed_article_id", "last_seen_at"],
            unique_fields=["article", "feed"],
        )

    def _update_article_urls_from_feed(self, feed: Feed, feed_data: FeedData):
        """Update the URLs of the articles in the feed if they changed.

        We assume the previous URL is now a redirection to the new one. This assumes the article id
        in the feed is stable. If not, the existing article will be found by its URLs.
        If both have changed, a new article will be created (this shouldn't happen and duplication
        is accepted in this case).
        Note: the new URL can already correspond to an existing article. In this case, the old URL
        is kept for the article if it exists. The link between the feed and the proper article will
        be created by another function.
        """
        feed_article_id_to_article_url = {
            article.external_article_id: article.url for article in feed_data.articles
        }
        articles_to_update = []
        article_urls_already_exist = set(
            Article.objects.filter(
                user=feed.user, url__in=feed_article_id_to_article_url.values()
            ).values_list("url", flat=True)
        )
        for feed_article in (
            FeedArticle.objects.all()
            .filter(
                feed=feed,
                feed_article_id__in=[article.external_article_id for article in feed_data.articles],
                article__isnull=False,
            )
            .prefetch_related("article")
        ):
            new_article_url = feed_article_id_to_article_url[feed_article.feed_article_id]
            if (
                feed_article.article is None
                or feed_article.article.url in article_urls_already_exist
                or new_article_url in article_urls_already_exist
            ):
                continue

            feed_article.article.url = new_article_url
            articles_to_update.append(feed_article.article)

        Article.objects.bulk_update(articles_to_update, fields=["url"])

    def _mark_republished_articles_as_unread(self, feed: Feed, feed_data: FeedData):
        Article.objects.filter(
            feed_articles__feed=feed,
            feed_articles__feed_article_id__in=[
                article.external_article_id for article in feed_data.articles
            ],
            feed_articles__last_seen_at__lt=utcnow()
            - timedelta(days=feeds_constants.DELAY_BEFORE_REPUBLICATION),
            read_at__lt=utcnow() - timedelta(days=feeds_constants.DELAY_BEFORE_REPUBLICATION),
        ).update(read_at=None)

    def _delete_feed_article_linked_wrong_article(
        self, feed: Feed, save_results: list[SaveArticleResult]
    ):
        """Delete the feed article if the article is linked to the wrong article.

        This can happen if the feed is already linked with an article with a URL, but this update
        would require the URL to be updated. If an article with this URL already exists, the linked
        article cannot be updated. Hence, the need to delete the old link to be able to recreate it
        with the proper article. It is preferable than to have multiple links with the same ids.

        Note: This shouldn't happen very often.
        """
        filters = models.Q()
        for result in save_results:
            filters |= models.Q(feed_article_id=result.article_id_in_data) & ~models.Q(
                article=result.article
            )

        FeedArticle.objects.filter(filters, feed=feed).delete()

    @transaction.atomic()
    def log_error(self, feed: Feed, error_message: str, technical_debug_data: dict | None = None):
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.FAILURE,
            error_message=error_message,
            feed=feed,
            technical_debug_data=technical_debug_data,
        )
        if FeedUpdate.objects.must_disable_feed(feed):
            message = _("We failed too many times to fetch the feed")
            feed.disable(message)
            feed.save()
            Notification.objects.create(
                user=feed.user,
                title=_("Feed '%s' was disabled") % feed.title,
                content=str(message),
                info_link=reverse("feeds:edit_feed", kwargs={"feed_id": feed.id}),
                info_link_text=str(_("Edit feed")),
            )

    def log_not_modified(self, feed: Feed):
        FeedUpdate.objects.create(
            status=feeds_constants.FeedUpdateStatus.NOT_MODIFIED,
            feed=feed,
        )

    def export(self, user: User, *, updated_since: datetime | None = None) -> list[dict[str, Any]]:
        feeds = []
        for feed in self.get_queryset().for_export(user, updated_since=updated_since):
            feed_category = feed.category
            feeds.append({
                "category_id": feed_category.id if feed_category else "",
                "category_title": feed_category.title if feed_category else "",
                "feed_id": feed.id if feed else "",
                "feed_title": feed.title if feed else "",
                "feed_url": feed.feed_url if feed else "",
                "feed_site_url": feed.site_url if feed else "",
                "article_id": "",
                "article_title": "",
                "article_url": "",
                "article_content": "",
                "article_date_published": "",
                "article_date_updated": "",
                "article_authors": "",
                "article_tags": "",
                "article_read_at": "",
                "article_is_favorite": "",
                "article_lang": "",
            })

        return feeds


class Feed(models.Model):
    feed_url = models.URLField()
    site_url = models.URLField()
    enabled = models.GeneratedField(
        expression=models.Case(
            models.When(models.Q(disabled_at__isnull=True), then=True), default=False
        ),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    disabled_reason = models.TextField(blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    # We store some feeds metadata, so we don't have to fetch when we need it.
    title = models.CharField(max_length=feeds_constants.FEED_TITLE_MAX_LENGTH)
    slug = models.SlugField(max_length=feeds_constants.FEED_TITLE_MAX_LENGTH, blank=True)
    description = models.TextField(blank=True)
    feed_type = models.CharField(
        choices=feeds_constants.SupportedFeedType.choices,
        max_length=100,
    )
    refresh_delay = models.CharField(
        choices=feeds_constants.FeedRefreshDelays.choices,
        max_length=100,
        default=feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
    )
    article_retention_time = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "Define for how long in days to keep read articles associated with this feed. Use 0 to "
            "always keep the articles."
        ),
    )
    open_original_url_by_default = models.BooleanField(default=False)

    user = models.ForeignKey("users.User", related_name="feeds", on_delete=models.CASCADE)
    category = models.ForeignKey(
        "feeds.FeedCategory",
        related_name="feeds",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    articles = models.ManyToManyField(
        "reading.Article",
        related_name="feeds",
        through="feeds.FeedArticle",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FeedManager()

    class Meta(TypedModelMeta):
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                "feed_url", "user", name="%(app_label)s_%(class)s_feed_url_unique"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_feed_type_valid",
                condition=models.Q(
                    feed_type__in=feeds_constants.SupportedFeedType.names,
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_refresh_delay_type_valid",
                condition=models.Q(
                    refresh_delay__in=feeds_constants.FeedRefreshDelays.names,
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_disabled_reason_disabled_at_empty_when_enabled",
                condition=models.Q(
                    disabled_reason="",
                    disabled_at__isnull=True,
                    enabled=True,
                )
                | models.Q(enabled=False),
            ),
        ]

    def __str__(self):
        category_title = self.category.title if self.category else "None"
        return f"Feed(title={self.title}, feed_type={self.feed_type}, category={category_title})"

    def disable(self, reason=""):
        self.disabled_reason = reason
        self.disabled_at = utcnow()
        self.enabled = False

    def enable(self):
        self.disabled_reason = ""
        self.disabled_at = None
        self.enabled = True
