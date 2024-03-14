from __future__ import annotations

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from legadilo.users.models import User

from ..constants import SupportedFeedType
from ..utils.feed_parsing import FeedMetadata
from .article import Article
from .feed_update import FeedUpdate


class FeedQuerySet(models.QuerySet):
    def only_feeds_to_update(self, feed_ids: list[int] | None = None):
        feeds_to_update = self.filter(enabled=True)
        if feed_ids:
            feeds_to_update = feeds_to_update.filter(id__in=feed_ids)

        return feeds_to_update


class FeedManager(models.Manager["Feed"]):
    _hints: dict

    def get_queryset(self) -> FeedQuerySet:
        return FeedQuerySet(model=self.model, using=self._db, hints=self._hints)

    @transaction.atomic()
    def create_from_metadata(self, feed_metadata: FeedMetadata, user: User) -> Feed:
        feed = self.create(
            feed_url=feed_metadata.feed_url,
            site_url=feed_metadata.site_url,
            title=feed_metadata.title,
            description=feed_metadata.description,
            feed_type=feed_metadata.feed_type,
            user=user,
        )
        Article.objects.update_or_create_from_articles_list(feed_metadata.articles, feed.pk)
        FeedUpdate.objects.create(
            success=True,
            feed_etag=feed_metadata.etag,
            feed_last_modified=feed_metadata.last_modified,
            feed=feed,
        )
        return feed

    @transaction.atomic()
    def update_feed(self, feed: Feed, feed_metadata: FeedMetadata):
        Article.objects.update_or_create_from_articles_list(feed_metadata.articles, feed.id)
        FeedUpdate.objects.create(
            success=True,
            feed_etag=feed_metadata.etag,
            feed_last_modified=feed_metadata.last_modified,
            feed=feed,
        )

    @transaction.atomic()
    def disable(self, feed: Feed, error_message: str):
        FeedUpdate.objects.create(
            success=False,
            error_message=error_message,
            feed=feed,
        )
        if FeedUpdate.objects.must_disable_feed(feed):
            feed.disable(_("We failed too many times to fetch the feed"))
            feed.save()


class Feed(models.Model):
    feed_url = models.URLField()
    site_url = models.URLField()
    enabled = models.BooleanField(default=True)
    disabled_reason = models.CharField()

    # We store some feeds metadata, so we don't have to fetch when we need it.
    title = models.CharField()
    description = models.TextField()
    feed_type = models.CharField(choices=SupportedFeedType)

    user = models.ForeignKey("users.User", related_name="feeds", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = FeedManager()

    class Meta:
        constraints = (
            models.UniqueConstraint("feed_url", "user", name="feeds_Feed_feed_url_unique"),
            models.CheckConstraint(
                name="feeds_Feed_feed_type_valid",
                check=models.Q(
                    feed_type__in=SupportedFeedType.names,
                ),
            ),
            models.CheckConstraint(
                name="feeds_Feed_disabled_reason_empty_when_enabled",
                check=models.Q(
                    disabled_reason="",
                    enabled=True,
                )
                | models.Q(enabled=False),
            ),
        )

    def __str__(self):
        return f"Feed(title={self.title})"

    def disable(self, reason=""):
        self.disabled_reason = reason
        self.enabled = False
