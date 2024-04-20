from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self, assert_never, cast

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.paginator import Paginator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta
from slugify import slugify

from legadilo.utils.validators import list_of_strings_json_schema_validator

from ...utils.time import utcnow
from .. import constants
from ..utils.feed_parsing import FeedArticle
from .tag import ArticleTag

if TYPE_CHECKING:
    from .feed import Feed
    from .reading_list import ReadingList
    from .tag import Tag


def _build_filters_from_reading_list(reading_list: ReadingList) -> models.Q:
    filters = models.Q(feed__user=reading_list.user)

    if reading_list.read_status == constants.ReadStatus.ONLY_READ:
        filters &= models.Q(is_read=True)
    elif reading_list.read_status == constants.ReadStatus.ONLY_UNREAD:
        filters &= models.Q(is_read=False)

    if reading_list.favorite_status == constants.FavoriteStatus.ONLY_FAVORITE:
        filters &= models.Q(is_favorite=True)
    elif reading_list.favorite_status == constants.FavoriteStatus.ONLY_NON_FAVORITE:
        filters &= models.Q(is_favorite=False)

    if reading_list.for_later_status == constants.ForLaterStatus.ONLY_FOR_LATER:
        filters &= models.Q(is_for_later=True)
    elif reading_list.for_later_status == constants.ForLaterStatus.ONLY_NOT_FOR_LATER:
        filters &= models.Q(is_for_later=False)

    if reading_list.articles_max_age_unit != constants.ArticlesMaxAgeUnit.UNSET:
        filters &= models.Q(
            published_at__gt=utcnow()
            - relativedelta(**{  # type: ignore[arg-type]
                reading_list.articles_max_age_unit.lower(): reading_list.articles_max_age_value
            })
        )

    articles_reading_time_operator = cast(
        constants.ArticlesReadingTimeOperator, reading_list.articles_reading_time_operator
    )
    match articles_reading_time_operator:
        case constants.ArticlesReadingTimeOperator.UNSET:
            pass
        case constants.ArticlesReadingTimeOperator.MORE_THAN:
            filters &= models.Q(reading_time__gte=reading_list.articles_reading_time)
        case constants.ArticlesReadingTimeOperator.LESS_THAN:
            filters &= models.Q(reading_time__lte=reading_list.articles_reading_time)
        case _:
            assert_never(reading_list.articles_reading_time_operator)

    filters &= _get_tags_filters(reading_list)

    return filters


def _get_tags_filters(reading_list: ReadingList) -> models.Q:
    filters = models.Q()
    tags_to_include = []
    tags_to_exclude = []
    for reading_list_tag in reading_list.reading_list_tags.all():
        filter_type = cast(constants.ReadingListTagFilterType, reading_list_tag.filter_type)
        match filter_type:
            case constants.ReadingListTagFilterType.INCLUDE:
                tags_to_include.append(reading_list_tag.tag_id)
            case constants.ReadingListTagFilterType.EXCLUDE:
                tags_to_exclude.append(reading_list_tag.tag_id)
            case _:
                assert_never(reading_list_tag.filter_type)

    if tags_to_include:
        operator = _get_reading_list_tags_sql_operator(
            constants.ReadingListTagOperator(reading_list.include_tag_operator)
        )
        filters &= models.Q(**{f"alias_tag_ids_for_article__{operator}": tags_to_include})
    if tags_to_exclude:
        operator = _get_reading_list_tags_sql_operator(
            constants.ReadingListTagOperator(reading_list.exclude_tag_operator)
        )
        filters &= ~models.Q(**{f"alias_tag_ids_for_article__{operator}": tags_to_exclude})
    return filters


def _get_reading_list_tags_sql_operator(
    reading_list_operator: constants.ReadingListTagOperator,
) -> Literal["contains", "overlap"]:
    match reading_list_operator:
        case constants.ReadingListTagOperator.ALL:
            return "contains"
        case constants.ReadingListTagOperator.ANY:
            return "overlap"


def _build_prefetch_article_tags():
    return models.Prefetch(
        "article_tags",
        queryset=ArticleTag.objects.get_queryset().for_reading_list(),
        to_attr="tags_to_display",
    )


class ArticleQuerySet(models.QuerySet["Article"]):
    def for_reading_list_filtering(self) -> Self:
        return self.alias(
            alias_tag_ids_for_article=ArrayAgg(
                "article_tags__tag_id",
                filter=~models.Q(article_tags__tagging_reason=constants.TaggingReason.DELETED),
                default=models.Value([]),
            ),
        )

    def for_reading_list(self, reading_list: ReadingList) -> Self:
        return (
            self.for_reading_list_filtering()
            .filter(_build_filters_from_reading_list(reading_list))
            .select_related("feed")
            .prefetch_related(_build_prefetch_article_tags())
        )

    def for_tag(self, tag: Tag) -> Self:
        return (
            self.filter(article_tags__tag=tag)
            .exclude(article_tags__tagging_reason=constants.TaggingReason.DELETED)
            .select_related("feed")
            .prefetch_related(_build_prefetch_article_tags())
        )

    def for_details(self) -> Self:
        return self.select_related("feed").prefetch_related(_build_prefetch_article_tags())


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
                title=article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH],
                slug=slugify(article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH]),
                summary=article_data.summary,
                content=article_data.content,
                reading_time=article_data.nb_words // feed.user.settings.default_reading_time,
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
                "slug",
                "summary",
                "content",
                "reading_time",
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

    def get_articles_of_reading_list(self, reading_list: ReadingList) -> Paginator[Article]:
        return Paginator(
            self.get_queryset().for_reading_list(reading_list).order_by("-published_at", "id"),
            constants.MAX_ARTICLE_PER_PAGE,
        )

    def count_articles_of_reading_lists(self, reading_lists: list[ReadingList]) -> dict[str, int]:
        aggregation = {
            reading_list.slug: models.Count(
                "id", filter=_build_filters_from_reading_list(reading_list)
            )
            for reading_list in reading_lists
        }
        return self.get_queryset().for_reading_list_filtering().aggregate(**aggregation)

    def get_articles_of_tag(self, tag: Tag) -> Paginator[Article]:
        return Paginator(self.get_queryset().for_tag(tag), constants.MAX_ARTICLE_PER_PAGE)


class Article(models.Model):
    title = models.CharField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH)
    slug = models.SlugField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH)
    summary = models.TextField()
    content = models.TextField(blank=True)
    reading_time = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "How much time in minutes is needed to read this article. If not specified, "
            "it will be calculated automatically from content length. If we don't have content, "
            "we will use 0."
        ),
    )
    authors = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    contributors = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    feed_tags = models.JSONField(validators=[list_of_strings_json_schema_validator], blank=True)
    link = models.URLField()
    published_at = models.DateTimeField()
    article_feed_id = models.CharField(help_text=_("The id of the article in the feed."))

    read_at = models.DateTimeField(null=True, blank=True)
    is_read = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Q(read_at__isnull=False),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    was_opened = models.GeneratedField(  # type: ignore[attr-defined]
        expression=models.Q(opened_at__isnull=False),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    is_favorite = models.BooleanField(default=False)
    is_for_later = models.BooleanField(default=False)

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

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)

        return super().save(*args, **kwargs)

    def update_article(self, action: constants.UpdateArticleActions):
        match action:
            case constants.UpdateArticleActions.MARK_AS_READ:
                self.read_at = utcnow()
            case constants.UpdateArticleActions.MARK_AS_UNREAD:
                self.read_at = None
            case constants.UpdateArticleActions.MARK_AS_FAVORITE:
                self.is_favorite = True
            case constants.UpdateArticleActions.UNMARK_AS_FAVORITE:
                self.is_favorite = False
            case constants.UpdateArticleActions.MARK_AS_FOR_LATER:
                self.is_for_later = True
            case constants.UpdateArticleActions.UNMARK_AS_FOR_LATER:
                self.is_for_later = False
            case constants.UpdateArticleActions.MARK_AS_OPENED:
                self.opened_at = utcnow()
            case _:
                assert_never(action)
