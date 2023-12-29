from django.db import models

from legadilo.users.models import User

from ..constants import SupportedFeedType
from ..utils.feed_metadata import get_feed_metadata


class FeedManager(models.Manager):
    async def create_from_url(self, url: str, user: User):
        feed_medata = await get_feed_metadata(url)
        return await self.acreate(
            feed_url=feed_medata.feed_url,
            site_url=feed_medata.site_url,
            title=feed_medata.title,
            description=feed_medata.description,
            feed_type=feed_medata.feed_type,
            user=user,
        )


class Feed(models.Model):
    feed_url = models.URLField()
    site_url = models.URLField()
    enabled = models.BooleanField(default=True)

    # We store some feeds metadata so we don't have to fetch when we need it.
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
        )

    def __str__(self):
        return f"Feed(title={self.title})"
