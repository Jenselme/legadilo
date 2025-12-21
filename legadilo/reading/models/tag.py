# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Self, TypedDict

from django.core.paginator import Paginator
from django.db import models, transaction
from slugify import slugify

from legadilo.core import constants as core_constants
from legadilo.core.utils.types import FormChoices
from legadilo.reading import constants
from legadilo.users.models import User

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.reading.models.article import Article, ArticleQuerySet
    from legadilo.reading.models.articles_group import ArticlesGroup
    from legadilo.reading.models.reading_list import ReadingList
else:
    TypedModelMeta = object
    ReadingList = object


class SubTag(TypedDict):
    title: str
    slug: str


TagsHierarchy = dict[str, list[SubTag]]


class SubTagMappingManager(models.Manager):
    def get_selected_mappings(self, tag: Tag) -> FormChoices:
        return list(
            self
            .filter(base_tag=tag)
            .values_list("sub_tag__slug", flat=True)
            .order_by("sub_tag__title")
        )

    @transaction.atomic()
    def associate_tag_with_sub_tags(
        self, tag: Tag, sub_tag_slugs: list[str], *, clear_existing: bool = False
    ):
        if clear_existing:
            tag.sub_tag_mappings.all().delete()

        sub_tags = Tag.objects.get_or_create_from_list(tag.user, sub_tag_slugs)
        sub_tag_mappings = [self.model(base_tag=tag, sub_tag=sub_tag) for sub_tag in sub_tags]
        self.bulk_create(sub_tag_mappings)


class SubTagMapping(models.Model):
    base_tag = models.ForeignKey(
        "reading.Tag", related_name="sub_tag_mappings", on_delete=models.CASCADE
    )
    sub_tag = models.ForeignKey(
        "reading.Tag", related_name="base_tag_mappings", on_delete=models.CASCADE
    )

    objects = SubTagMappingManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "base_tag", "sub_tag", name="%(app_label)s_%(class)s_unique_sub_tag_mapping_for_tag"
            )
        ]

    def __str__(self):
        return f"SubTagMapping(base_tag={self.base_tag}, sub_tag={self.sub_tag})"


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

    def get_all_choices_with_hierarchy(self, user: User) -> tuple[FormChoices, TagsHierarchy]:
        choices: FormChoices = []
        hierarchy: TagsHierarchy = {}

        for tag in (
            self.get_queryset().for_user(user).prefetch_related("sub_tags").order_by("title", "id")
        ):
            choices.append((tag.slug, tag.title))
            hierarchy[tag.slug] = [
                {"title": sub_tag.title, "slug": sub_tag.slug} for sub_tag in tag.sub_tags.all()
            ]

        return choices, hierarchy

    def get_slugs_to_ids(self, user: User, slugs: Iterable[str]) -> dict[str, int]:
        return {
            slug: id_
            for id_, slug in self
            .get_queryset()
            .for_user(user)
            .for_slugs(slugs)
            .values_list("id", "slug")
        }

    @transaction.atomic()
    def get_or_create_from_list(self, user: User, titles_or_slugs: Iterable[str]) -> list[Tag]:
        existing_tags = list(
            Tag.objects
            .get_queryset()
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

    def list_for_admin(self, user: User, searched_text: str = "") -> list[Tag]:
        qs = (
            self
            .get_queryset()
            .for_user(user)
            .annotate(annot_articles_count=models.Count("articles"))
            .order_by("title")
        )

        if searched_text:
            qs = qs.filter(title__icontains=searched_text)

        return list(qs)


class Tag(models.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    sub_tags = models.ManyToManyField(
        "reading.Tag", related_name="base_tags", through=SubTagMapping
    )

    user = models.ForeignKey("users.User", related_name="tags", on_delete=models.CASCADE)
    articles = models.ManyToManyField(
        "reading.Article", related_name="tags", through="reading.ArticleTag"
    )
    feeds = models.ManyToManyField("feeds.Feed", related_name="tags", through="feeds.FeedTag")
    reading_lists = models.ManyToManyField(
        "reading.ReadingList", related_name="tags", through="reading.ReadingListTag"
    )
    article_groups = models.ManyToManyField(
        "reading.ArticlesGroup", related_name="tags", through="reading.ArticlesGroupTag"
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
    def for_articles_and_tags(self, articles: Iterable[Article], tags: Iterable[Tag]) -> Self:
        return self.filter(
            article_id__in=[article.id for article in articles], tag_id__in=[tag.id for tag in tags]
        )


class ArticleTagManager(models.Manager["ArticleTag"]):
    _hints: dict

    def get_queryset(self) -> ArticleTagQuerySet:
        return ArticleTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_selected_values(self) -> list[str]:
        return list(self.get_queryset().values_list("tag__slug", flat=True))

    def associate_articles_with_tags(
        self, all_articles: Sequence[Article] | ArticleQuerySet, tags: Iterable[Tag]
    ):
        # Can associate tags with lots of (thousands!) articles at once. To prevent high memory
        # usage, use a paginator.
        paginator: Paginator[Article] = Paginator(
            all_articles, core_constants.PER_PAGE_FOR_BULK_OPERATIONS
        )
        for page in paginator:
            existing_article_tag_urls = list(
                self
                .get_queryset()
                .for_articles_and_tags(page.object_list, tags)
                .values_list("article_id", "tag_id")
            )
            article_tags_to_create = [
                self.model(article=article, tag=tag)
                for article in page.object_list
                for tag in tags
                if (article.id, tag.id) not in existing_article_tag_urls
            ]
            self.bulk_create(article_tags_to_create)

    def dissociate_article_with_tags_not_in_list(self, article: Article, tags: Iterable[Tag]):
        existing_article_tag_slugs = set(article.tags.all().values_list("slug", flat=True))
        tag_slugs_to_keep = {tag.slug for tag in tags}
        article_tag_slugs_to_delete = existing_article_tag_slugs - tag_slugs_to_keep

        if article_tag_slugs_to_delete:
            article.article_tags.filter(tag__slug__in=article_tag_slugs_to_delete).delete()

    def dissociate_articles_with_tags(
        self, all_articles: Sequence[Article] | ArticleQuerySet, tags: Iterable[Tag]
    ):
        paginator: Paginator[Article] = Paginator(
            all_articles, core_constants.PER_PAGE_FOR_BULK_OPERATIONS
        )
        for page in paginator:
            self.get_queryset().for_articles_and_tags(page.object_list, tags).delete()


class ArticleTag(models.Model):
    article = models.ForeignKey(
        "reading.Article", related_name="article_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey("reading.Tag", related_name="article_tags", on_delete=models.CASCADE)

    objects = ArticleTagManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "article", "tag", name="%(app_label)s_%(class)s_tagged_once_per_article"
            ),
        ]
        ordering = ["article_id", "tag__title", "tag_id"]

    def __str__(self):
        return f"ArticleTag(article={self.article}, tag={self.tag})"


class ReadingListTagQuerySet(models.QuerySet["ReadingListTag"]):
    def for_reading_list(self, filter_type: constants.ReadingListTagFilterType):
        return (
            self
            .select_related("tag")
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
    def associate_reading_list_with_tags(
        self,
        reading_list: ReadingList,
        tags: Iterable[Tag],
        filter_type: constants.ReadingListTagFilterType,
    ):
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
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_filter_type_valid",
                condition=models.Q(
                    filter_type__in=constants.ReadingListTagFilterType.names,
                ),
            ),
        ]
        ordering = ["tag__title", "tag_id"]

    def __str__(self):
        return f"ReadingListTag(reading_list={self.reading_list}, tag={self.tag})"


class ArticlesGroupTagQuerySet(models.QuerySet["ArticlesGroupTag"]):
    pass


class ArticlesGroupTagManager(models.Manager["ArticlesGroupTag"]):
    _hints: dict

    def get_queryset(self) -> ArticlesGroupTagQuerySet:
        return ArticlesGroupTagQuerySet(model=self.model, using=self._db, hints=self._hints)

    @transaction.atomic()
    def associate_group_with_tags(self, article_group: ArticlesGroup, tags: list[Tag]):
        article_group.article_group_tags.all().delete()
        group_tags = [self.model(article_group=article_group, tag=tag) for tag in tags]
        self.bulk_create(group_tags)


class ArticlesGroupTag(models.Model):
    article_group = models.ForeignKey(
        "reading.ArticlesGroup", related_name="article_group_tags", on_delete=models.CASCADE
    )
    tag = models.ForeignKey(
        "reading.Tag", related_name="article_group_tags", on_delete=models.CASCADE
    )

    objects = ArticlesGroupTagManager()

    class Meta(TypedModelMeta):
        constraints = (
            models.UniqueConstraint(
                "article_group", "tag", name="%(app_label)s_%(class)s_tagged_once_per_article_group"
            ),
        )
        ordering = ("tag__title", "tag_id")

    def __str__(self):
        return f"ArticlesGroupTag(article_group={self.article_group}, tag={self.tag})"
