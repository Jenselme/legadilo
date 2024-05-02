from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Self

from django.db import models, transaction
from slugify import slugify

from ...users.models import User
from .. import constants

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from .article import Article
    from .feed import Feed
else:
    TypedModelMeta = object


class TagQuerySet(models.QuerySet["Tag"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)

    def for_slugs(self, slugs: Iterable[str]) -> Self:
        return self.filter(slug__in=slugs)


class TagManager(models.Manager["Tag"]):
    _hints: dict

    def get_queryset(self) -> TagQuerySet:
        return TagQuerySet(self.model, using=self._db, hints=self._hints)

    def get_all_choices(self, user: User) -> list[tuple[str, str]]:
        return list(self.get_queryset().for_user(user).values_list("slug", "name"))

    @transaction.atomic()
    def get_or_create_from_list(self, user: User, names_or_slugs: list[str]) -> list[Tag]:
        existing_tags = list(
            Tag.objects.get_queryset()
            .for_user(user)
            .for_slugs([slugify(name_or_slug) for name_or_slug in names_or_slugs])
        )
        existing_slugs = {tag.slug for tag in existing_tags}
        tags_to_create = [
            self.model(name=name_or_slug, slug=slugify(name_or_slug), user=user)
            for name_or_slug in names_or_slugs
            if slugify(name_or_slug) not in existing_slugs
        ]
        self.bulk_create(tags_to_create)

        return [*existing_tags, *tags_to_create]


class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    user = models.ForeignKey("users.User", related_name="tags", on_delete=models.CASCADE)
    articles = models.ManyToManyField(
        "feeds.Article", related_name="tags", through="feeds.ArticleTag"
    )
    feeds = models.ManyToManyField("feeds.Feed", related_name="tags", through="feeds.FeedTag")
    reading_lists = models.ManyToManyField(
        "feeds.ReadingList", related_name="tags", through="feeds.ReadingListTag"
    )

    objects = TagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "slug", "user_id", name="%(app_label)s_%(class)s_tag_slug_unique_for_user"
            )
        ]
        ordering = ["name", "id"]

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
            .annotate(name=models.F("tag__name"), slug=models.F("tag__slug"))
        )

    def for_articles_and_tags(self, articles: Iterable[Article], tags: Iterable[Tag]) -> Self:
        return self.filter(
            article_id__in=[article.id for article in articles], tag_id__in=[tag.id for tag in tags]
        )

    def for_deleted_links(self, links: Iterable[tuple[int, int]]) -> Self:
        article_ids = [link[0] for link in links]
        tag_ids = [link[1] for link in links]

        return self.filter(
            article_id__in=article_ids,
            tag_id__in=tag_ids,
            tagging_reason=constants.TaggingReason.DELETED,
        )


class ArticleTagManager(models.Manager["ArticleTag"]):
    _hints: dict

    def get_queryset(self) -> ArticleTagQuerySet:
        return ArticleTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_selected_values(self) -> list[str]:
        return list(self.get_queryset().for_reading_list().values_list("slug", flat=True))

    def associate_articles_with_tags(
        self,
        articles: Iterable[Article],
        tags: Iterable[Tag],
        tagging_reason: constants.TaggingReason,
        *,
        readd_deleted=False,
    ):
        existing_article_tag_links = list(
            self.get_queryset()
            .for_articles_and_tags(articles, tags)
            .values_list("article_id", "tag_id")
        )
        article_tags_to_create = [
            self.model(article=article, tag=tag, tagging_reason=tagging_reason)
            for article in articles
            for tag in tags
            if (article.id, tag.id) not in existing_article_tag_links
        ]
        self.bulk_create(article_tags_to_create)

        if readd_deleted:
            self.get_queryset().for_deleted_links(existing_article_tag_links).update(
                tagging_reason=constants.TaggingReason.ADDED_MANUALLY
            )

    def dissociate_article_with_tags_not_in_list(self, article: Article, tags: Iterable[Tag]):
        existing_article_tag_slugs = set(article.tags.all().values_list("slug", flat=True))
        tag_slugs_to_keep = {tag.slug for tag in tags}
        article_tag_slugs_to_delete = existing_article_tag_slugs - tag_slugs_to_keep

        if article_tag_slugs_to_delete:
            article.article_tags.filter(tag__slug__in=article_tag_slugs_to_delete).update(
                tagging_reason=constants.TaggingReason.DELETED
            )


class ArticleTag(models.Model):
    article = models.ForeignKey(
        "feeds.Article", related_name="article_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("feeds.Tag", related_name="article_tags", on_delete=models.CASCADE)

    tagging_reason = models.CharField(
        choices=constants.TaggingReason.choices,
        default=constants.TaggingReason.ADDED_MANUALLY,
        max_length=100,
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
        ordering = ["article_id", "tag__name", "tag_id"]

    def __str__(self):
        return (
            f"ArticleTag(article={self.article}, tag={self.tag},"
            f"tagging_reason={self.tagging_reason})"
        )


class FeedTagQuerySet(models.QuerySet["FeedTag"]):
    pass


class FeedTagManager(models.Manager["FeedTag"]):
    _hints: dict

    def get_queryset(self) -> FeedTagQuerySet:
        return FeedTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def associate_feed_with_tags(self, feed: Feed, tags: Iterable[Tag]):
        feed_tags = [self.model(feed=feed, tag=tag) for tag in tags]
        self.bulk_create(feed_tags, ignore_conflicts=True, unique_fields=["feed_id", "tag_id"])


class FeedTag(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_tags", on_delete=models.CASCADE)
    tag = models.ForeignKey("feeds.Tag", related_name="feed_tags", on_delete=models.CASCADE)

    objects = FeedTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "tag", name="%(app_label)s_%(class)s_tagged_once_per_feed"
            )
        ]
        ordering = ["tag__name", "tag_id"]

    def __str__(self):
        return f"FeedTag(feed={self.feed}, tag={self.tag})"


class ReadingListTag(models.Model):
    reading_list = models.ForeignKey(
        "feeds.ReadingList", related_name="reading_list_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("feeds.Tag", related_name="reading_list_tags", on_delete=models.CASCADE)

    filter_type = models.CharField(
        choices=constants.ReadingListTagFilterType.choices,
        default=constants.ReadingListTagFilterType.INCLUDE,
        max_length=100,
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
        ordering = ["tag__name", "tag_id"]

    def __str__(self):
        return f"ReadingListTag(reading_list={self.reading_list}, tag={self.tag})"
