from django.db import models
from django_stubs_ext.db.models import TypedModelMeta
from slugify import slugify

from .. import constants


class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    user = models.ForeignKey("users.User", related_name="tags", on_delete=models.CASCADE)
    article_tags = models.ManyToManyField(
        "feeds.Article", related_name="tags", through="feeds.ArticleTag"
    )
    feed_tags = models.ManyToManyField("feeds.Feed", related_name="tags", through="feeds.FeedTag")

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "slug", "user_id", name="%(app_label)s_%(class)s_tag_slug_unique_for_user"
            )
        ]

    def __str__(self):
        return f"Tag(name={self.name}, user={self.user})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        return super().save(*args, **kwargs)


class ArticleTag(models.Model):
    article = models.ForeignKey(
        "feeds.Article", related_name="article_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("feeds.Tag", related_name="articles", on_delete=models.CASCADE)

    tagging_reason = models.CharField(
        choices=constants.TaggingReason.choices, default=constants.TaggingReason.ADDED_MANUALLY
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_tagging_reason_valid",
                check=models.Q(
                    tagging_reason__in=constants.TaggingReason.names,
                ),
            ),
        ]

    def __str__(self):
        return (
            f"ArticleTag(article={self.article}, tag={self.tag},"
            f"tagging_reason={self.tagging_reason})"
        )


class FeedTag(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_tags", on_delete=models.CASCADE)
    tag = models.ForeignKey("feeds.Tag", related_name="feeds", on_delete=models.CASCADE)

    def __str__(self):
        return f"FeedTag(feed={self.feed}, tag={self.tag})"
