from __future__ import annotations

from typing import TYPE_CHECKING, Self

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from legadilo.utils.validators import list_of_strings_json_schema_validator

from ...utils.time import utcnow
from .. import constants
from ..utils.feed_parsing import FeedArticle
from .tag import ArticleTag

if TYPE_CHECKING:
    from .feed import Feed
    from .reading_list import ReadingList


class ArticleQuerySet(models.QuerySet["Article"]):
    def build_filters_from_reading_list(self, reading_list: ReadingList) -> models.Q:
        filters = models.Q(feed__user=reading_list.user)

        if reading_list.read_status == constants.ReadStatus.ONLY_READ:
            filters &= models.Q(is_read=True)
        elif reading_list.read_status == constants.ReadStatus.ONLY_UNREAD:
            filters &= models.Q(is_read=False)

        if reading_list.favorite_status == constants.FavoriteStatus.ONLY_FAVORITE:
            filters &= models.Q(is_favorite=True)
        elif reading_list.favorite_status == constants.FavoriteStatus.ONLY_NON_FAVORITE:
            filters &= models.Q(is_favorite=False)

        if reading_list.articles_max_age_unit != constants.ArticlesMaxAgeUnit.UNSET:
            filters &= models.Q(
                published_at__gt=utcnow()
                - relativedelta(**{  # type: ignore[arg-type]
                    reading_list.articles_max_age_unit.lower(): reading_list.articles_max_age_value
                })
            )

        return filters

    def for_reading_list(self, reading_list: ReadingList) -> Self:
        return (
            self.filter(self.build_filters_from_reading_list(reading_list))
            .select_related("feed")
            .prefetch_related(
                models.Prefetch(
                    "article_tags",
                    queryset=ArticleTag.objects.get_queryset().for_reading_list(),
                    to_attr="tags_to_display",
                )
            )
        )


class ArticleManager(models.Manager["Article"]):
    _hints: dict

    def get_queryset(self) -> ArticleQuerySet:
        return ArticleQuerySet(model=self.model, using=self._db, hints=self._hints)

    def update_or_create_from_articles_list(self, articles_data: list[FeedArticle], feed: Feed):
        if len(articles_data) == 0:
            return

        articles = [
            self.model(
                feed_id=feed.id,
                article_feed_id=article_data.article_feed_id,
                title=article_data.title,
                summary=article_data.summary,
                content=article_data.content,
                authors=article_data.authors,
                contributors=article_data.contributors,
                feed_tags=article_data.tags,
                link=article_data.link,
                published_at=article_data.published_at,
                updated_at=article_data.updated_at,
            )
            for article_data in articles_data
        ]
        created_articles = self.bulk_create(
            articles,
            update_conflicts=True,
            update_fields=[
                "title",
                "summary",
                "content",
                "authors",
                "contributors",
                "feed_tags",
                "link",
                "published_at",
                "updated_at",
            ],
            unique_fields=["feed_id", "article_feed_id"],
        )
        ArticleTag.objects.associate_articles_with_tags(created_articles, feed.tags.all())

    def get_articles_of_reading_list(self, reading_list: ReadingList) -> list[Article]:
        return list(self.get_queryset().for_reading_list(reading_list).order_by("-published_at"))


class Article(models.Model):
    title = models.CharField()
    summary = models.TextField()
    content = models.TextField(blank=True)
    authors = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    contributors = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    feed_tags = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    link = models.URLField()
    published_at = models.DateTimeField()
    article_feed_id = models.CharField(help_text=_("The id of the article in the feed."))

    is_read = models.BooleanField(default=False)
    was_opened = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)

    feed = models.ForeignKey("feeds.Feed", related_name="articles", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArticleManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "article_feed_id", "feed_id", name="%(app_label)s_%(class)s_article_unique_in_feed"
            ),
        ]

    def __str__(self):
        return (
            f"Article(feed_id={self.feed_id}, title={self.title}, published_at={self.published_at})"
        )
