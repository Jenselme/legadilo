from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, Self, assert_never, cast

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.paginator import Paginator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta
from slugify import slugify

from legadilo.utils.validators import list_of_strings_json_schema_validator

from ...utils.text import get_nb_words_from_html
from ...utils.time import utcnow
from .. import constants
from .tag import ArticleTag

if TYPE_CHECKING:
    from legadilo.users.models import User

    from ..utils.feed_parsing import ArticleData
    from .reading_list import ReadingList
    from .tag import Tag


def _build_filters_from_reading_list(reading_list: ReadingList) -> models.Q:
    filters = models.Q(user=reading_list.user)

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
            .prefetch_related(_build_prefetch_article_tags())
        )

    def for_tag(self, tag: Tag) -> Self:
        return (
            self.filter(article_tags__tag=tag)
            .exclude(article_tags__tagging_reason=constants.TaggingReason.DELETED)
            .prefetch_related(_build_prefetch_article_tags())
        )

    def for_details(self) -> Self:
        return self.prefetch_related(_build_prefetch_article_tags())


class ArticleManager(models.Manager["Article"]):
    _hints: dict

    def get_queryset(self) -> ArticleQuerySet:
        return ArticleQuerySet(model=self.model, using=self._db, hints=self._hints)

    def update_or_create_from_articles_list(
        self,
        user: User,
        articles_data: list[ArticleData],
        tags: Iterable[Tag],
        *,
        source_type: constants.ArticleSourceType,
        source_title: str,
    ) -> list[Article]:
        if len(articles_data) == 0:
            return []

        articles = [
            self.model(
                user=user,
                external_article_id=article_data.external_article_id,
                title=article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH],
                slug=slugify(article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH]),
                summary=article_data.summary,
                content=article_data.content,
                reading_time=get_nb_words_from_html(article_data.content)
                // user.settings.default_reading_time,
                authors=article_data.authors,
                contributors=article_data.contributors,
                external_tags=article_data.tags,
                link=article_data.link,
                published_at=article_data.published_at,
                updated_at=article_data.updated_at,
                initial_source_type=source_type,
                initial_source_title=source_title,
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
                "external_tags",
                "link",
                "published_at",
                "updated_at",
            ],
            unique_fields=["user", "link"],
        )
        ArticleTag.objects.associate_articles_with_tags(created_articles, tags)

        return created_articles

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
    authors = models.JSONField(
        validators=[list_of_strings_json_schema_validator], blank=True, default=list
    )
    contributors = models.JSONField(
        validators=[list_of_strings_json_schema_validator], blank=True, default=list
    )
    link = models.URLField()
    external_tags = models.JSONField(
        validators=[list_of_strings_json_schema_validator],
        blank=True,
        default=list,
        help_text=_("Tags of the article from the its source"),
    )
    external_article_id = models.CharField(
        default="", blank=True, help_text=_("The id of the article in the its source.")
    )

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

    user = models.ForeignKey("users.User", related_name="articles", on_delete=models.CASCADE)

    initial_source_type = models.CharField(
        default=constants.ArticleSourceType.FEED, choices=constants.ArticleSourceType.choices
    )
    initial_source_title = models.CharField()

    published_at = models.DateTimeField(
        null=True, blank=True, help_text=_("The date of publication of the article.")
    )
    updated_at = models.DateTimeField(
        null=True, blank=True, help_text=_("The last time the article was updated.")
    )
    obj_created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Technical date for the creation of the article in our database."),
    )
    obj_updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Technical date for the last update of the article in our database."),
    )

    objects = ArticleManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "user", "link", name="%(app_label)s_%(class)s_article_unique_for_user"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_initial_source_type_valid",
                check=models.Q(
                    initial_source_type__in=constants.ArticleSourceType.names,
                ),
            ),
        ]

    def __str__(self):
        return (
            f"Article(title={self.title}, initial_source_type={self.initial_source_type}, "
            f"initial_source_title={self.initial_source_title}, published_at={self.published_at})"
        )

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)

        return super().save(*args, **kwargs)

    def update_article_from_action(self, action: constants.UpdateArticleActions):
        match action:
            case constants.UpdateArticleActions.MARK_AS_READ:
                self.read_at = utcnow()
                self.is_read = True
            case constants.UpdateArticleActions.MARK_AS_UNREAD:
                self.read_at = None
                self.is_read = False
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
                self.was_opened = True
            case _:
                assert_never(action)
