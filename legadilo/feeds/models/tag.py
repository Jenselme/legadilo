from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models
from django_stubs_ext.db.models import TypedModelMeta
from slugify import slugify

from .. import constants

if TYPE_CHECKING:
    from .article import Article


class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    user = models.ForeignKey("users.User", related_name="tags", on_delete=models.CASCADE)
    article_tags = models.ManyToManyField(
        "feeds.Article", related_name="tags", through="feeds.ArticleTag"
    )
    feed_tags = models.ManyToManyField("feeds.Feed", related_name="tags", through="feeds.FeedTag")
    reading_list_tags = models.ManyToManyField(
        "feeds.ReadingList", related_name="tags", through="feeds.ReadingListTag"
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "slug", "user_id", name="%(app_label)s_%(class)s_tag_slug_unique_for_user"
            )
        ]

    def __str__(self):
        return f"Tag(name={self.name}, user={self.user})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)

        return super().save(*args, **kwargs)


class ArticleTagQuerySet(models.QuerySet["ArticleTag"]):
    def for_reading_list(self):
        return (
            self.exclude(tagging_reason=constants.TaggingReason.DELETED)
            .select_related("tag")
            .annotate(name=models.F("tag__name"))
        )


class ArticleTagManager(models.Manager["ArticleTag"]):
    _hints: dict

    def get_queryset(self) -> ArticleTagQuerySet:
        return ArticleTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def associate_articles_with_tags(self, articles: Iterable[Article], tags: Iterable[Tag]):
        article_tags = [
            self.model(article=article, tag=tag, tagging_reason=constants.TaggingReason.FROM_FEED)
            for article in articles
            for tag in tags
        ]
        self.bulk_create(
            article_tags, ignore_conflicts=True, unique_fields=["article_id", "tag_id"]
        )


class ArticleTag(models.Model):
    article = models.ForeignKey(
        "feeds.Article", related_name="article_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("feeds.Tag", related_name="articles", on_delete=models.CASCADE)

    tagging_reason = models.CharField(
        choices=constants.TaggingReason.choices, default=constants.TaggingReason.ADDED_MANUALLY
    )

    objects = ArticleTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_tagging_reason_valid",
                check=models.Q(
                    tagging_reason__in=constants.TaggingReason.names,
                ),
            ),
            models.UniqueConstraint(
                "article", "tag", name="%(app_label)s_%(class)s_tagged_once_per_article"
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

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "tag", name="%(app_label)s_%(class)s_tagged_once_per_feed"
            )
        ]

    def __str__(self):
        return f"FeedTag(feed={self.feed}, tag={self.tag})"


class ReadingListTag(models.Model):
    reading_list = models.ForeignKey(
        "feeds.ReadingList", related_name="reading_list_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("feeds.Tag", related_name="reading_lists", on_delete=models.CASCADE)

    filter_type = models.CharField(
        choices=constants.ReadingListTagFilterType.choices,
        default=constants.ReadingListTagFilterType.INCLUDE,
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "reading_list", "tag", name="%(app_label)s_%(class)s_tagged_once_per_reading_list"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_filter_type_valid",
                check=models.Q(
                    filter_type__in=constants.ReadingListTagFilterType.names,
                ),
            ),
        ]

    def __str__(self):
        return f"ReadingListTag(reading_list={self.reading_list}, tag={self.tag})"
