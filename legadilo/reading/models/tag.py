# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Self

from django.core.paginator import Paginator
from django.db import models, transaction
from slugify import slugify

from legadilo.core import constants as core_constants
from legadilo.core.forms import FormChoices
from legadilo.reading import constants
from legadilo.users.models import User

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.reading.models.article import Article, ArticleQuerySet
    from legadilo.reading.models.reading_list import ReadingList
else:
    TypedModelMeta = object
    ReadingList = object


class TagQuerySet(models.QuerySet["Tag"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)

    def for_slugs(self, slugs: Iterable[str]) -> Self:
        return self.filter(slug__in=slugs)


class TagManager(models.Manager["Tag"]):
    _hints: dict

    def get_queryset(self) -> TagQuerySet:
        return TagQuerySet(self.model, using=self._db, hints=self._hints)

    def get_all_choices(self, user: User) -> FormChoices:
        return list(self.get_queryset().for_user(user).values_list("slug", "title"))

    def get_slugs_to_ids(self, user: User, slugs: Iterable[str]) -> dict[str, int]:
        return {
            slug: id_
            for id_, slug in self.get_queryset()
            .for_user(user)
            .for_slugs(slugs)
            .values_list("id", "slug")
        }

    @transaction.atomic()
    def get_or_create_from_list(self, user: User, titles_or_slugs: list[str]) -> list[Tag]:
        existing_tags = list(
            Tag.objects.get_queryset()
            .for_user(user)
            .for_slugs([slugify(title_or_slug) for title_or_slug in titles_or_slugs])
        )
        existing_slugs = {tag.slug for tag in existing_tags}
        tags_to_create = [
            self.model(title=title_or_slug, slug=slugify(title_or_slug), user=user)
            for title_or_slug in titles_or_slugs
            if slugify(title_or_slug) not in existing_slugs
        ]
        self.bulk_create(tags_to_create)

        return [*existing_tags, *tags_to_create]


class Tag(models.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    user = models.ForeignKey("users.User", related_name="tags", on_delete=models.CASCADE)
    articles = models.ManyToManyField(
        "reading.Article", related_name="tags", through="reading.ArticleTag"
    )
    feeds = models.ManyToManyField("feeds.Feed", related_name="tags", through="feeds.FeedTag")
    reading_lists = models.ManyToManyField(
        "reading.ReadingList", related_name="tags", through="reading.ReadingListTag"
    )

    objects = TagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "slug", "user_id", name="%(app_label)s_%(class)s_tag_slug_unique_for_user"
            )
        ]
        ordering = ["title", "id"]

    def __str__(self):
        return f"Tag(title={self.title}, user={self.user})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)

        return super().save(*args, **kwargs)


class ArticleTagQuerySet(models.QuerySet["ArticleTag"]):
    def for_reading_list(self):
        return (
            self.exclude(tagging_reason=constants.TaggingReason.DELETED)
            .select_related("tag")
            .annotate(title=models.F("tag__title"), slug=models.F("tag__slug"))
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
        all_articles: Sequence[Article] | ArticleQuerySet,
        tags: Iterable[Tag],
        tagging_reason: constants.TaggingReason,
        *,
        readd_deleted=False,
    ):
        paginator: Paginator[Article] = Paginator(
            all_articles, core_constants.PER_PAGE_FOR_BULK_OPERATIONS
        )
        for page in paginator:
            existing_article_tag_links = list(
                self.get_queryset()
                .for_articles_and_tags(page.object_list, tags)
                .values_list("article_id", "tag_id")
            )
            article_tags_to_create = [
                self.model(article=article, tag=tag, tagging_reason=tagging_reason)
                for article in page.object_list
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

    def dissociate_articles_with_tags(
        self, all_articles: Sequence[Article] | ArticleQuerySet, tags: Iterable[Tag]
    ):
        paginator: Paginator[Article] = Paginator(
            all_articles, core_constants.PER_PAGE_FOR_BULK_OPERATIONS
        )
        for page in paginator:
            self.get_queryset().for_articles_and_tags(page.object_list, tags).update(
                tagging_reason=constants.TaggingReason.DELETED
            )


class ArticleTag(models.Model):
    article = models.ForeignKey(
        "reading.Article", related_name="article_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("reading.Tag", related_name="article_tags", on_delete=models.CASCADE)

    tagging_reason = models.CharField(
        choices=constants.TaggingReason.choices,
        default=constants.TaggingReason.ADDED_MANUALLY,
        max_length=100,
    )

    objects = ArticleTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.CheckConstraint(  # type: ignore[call-arg]
                name="%(app_label)s_%(class)s_tagging_reason_valid",
                condition=models.Q(
                    tagging_reason__in=constants.TaggingReason.names,
                ),
            ),
            models.UniqueConstraint(
                "article", "tag", name="%(app_label)s_%(class)s_tagged_once_per_article"
            ),
        ]
        ordering = ["article_id", "tag__title", "tag_id"]

    def __str__(self):
        return (
            f"ArticleTag(article={self.article}, tag={self.tag},"
            f"tagging_reason={self.tagging_reason})"
        )


class ReadingListTagQuerySet(models.QuerySet["ReadingListTag"]):
    def for_reading_list(self, filter_type: constants.ReadingListTagFilterType):
        return (
            self.select_related("tag")
            .filter(filter_type=filter_type)
            .annotate(title=models.F("tag__title"), slug=models.F("tag__slug"))
        )


class ReadingListTagManager(models.Manager["ReadingListTag"]):
    _hints: dict

    def get_queryset(self) -> ReadingListTagQuerySet:
        return ReadingListTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_selected_values(self, filter_type: constants.ReadingListTagFilterType) -> list[str]:
        return list(
            self.get_queryset().for_reading_list(filter_type).values_list("slug", flat=True)
        )

    @transaction.atomic()
    def associate_reading_list_with_tag_slugs(
        self,
        reading_list: ReadingList,
        tag_slugs: list[str],
        filter_type: constants.ReadingListTagFilterType,
    ):
        tags = Tag.objects.get_or_create_from_list(reading_list.user, tag_slugs)
        reading_list_tags = [
            self.model(reading_list=reading_list, tag=tag, filter_type=filter_type) for tag in tags
        ]
        reading_list.reading_list_tags.filter(filter_type=filter_type).delete()
        self.bulk_create(
            reading_list_tags,
            update_conflicts=True,
            update_fields=["filter_type"],
            unique_fields=["reading_list", "tag"],
        )


class ReadingListTag(models.Model):
    reading_list = models.ForeignKey(
        "reading.ReadingList", related_name="reading_list_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey(
        "reading.Tag", related_name="reading_list_tags", on_delete=models.CASCADE
    )

    filter_type = models.CharField(
        choices=constants.ReadingListTagFilterType.choices,
        default=constants.ReadingListTagFilterType.INCLUDE,
        max_length=100,
    )

    objects = ReadingListTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "reading_list", "tag", name="%(app_label)s_%(class)s_tagged_once_per_reading_list"
            ),
            models.CheckConstraint(  # type: ignore[call-arg]
                name="%(app_label)s_%(class)s_filter_type_valid",
                condition=models.Q(
                    filter_type__in=constants.ReadingListTagFilterType.names,
                ),
            ),
        ]
        ordering = ["tag__title", "tag_id"]

    def __str__(self):
        return f"ReadingListTag(reading_list={self.reading_list}, tag={self.tag})"
