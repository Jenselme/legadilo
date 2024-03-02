from django.db import models

from legadilo.users.models import User

from ..constants import SupportedFeedType
from ..utils.feed_parsing import get_feed_metadata
from .article import Article
from .feed_update import FeedUpdate


class FeedQuerySet(models.QuerySet):
    def only_feeds_to_update(self, feed_ids: list[int] | None = None):
        feeds_to_update = self.filter(enabled=True)
        if feed_ids:
            feeds_to_update = feeds_to_update.filter(id__in=feed_ids)

        return feeds_to_update


class FeedManager(models.Manager):
    _hints: dict

    def get_queryset(self) -> FeedQuerySet:
        return FeedQuerySet(model=self.model, using=self._db, hints=self._hints)

    async def create_from_url(self, url: str, user: User):
        feed_medata = await get_feed_metadata(url)
        feed = await self.acreate(
            feed_url=feed_medata.feed_url,
            site_url=feed_medata.site_url,
            title=feed_medata.title,
            description=feed_medata.description,
            feed_type=feed_medata.feed_type,
            user=user,
        )
        await Article.objects.update_or_create_from_articles_list(feed_medata.articles, feed.pk)
        await FeedUpdate.objects.acreate(
            success=True,
            feed_etag=feed_medata.etag,
            feed_last_modified=feed_medata.last_modified,
            feed=feed,
        )
        return feed


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
