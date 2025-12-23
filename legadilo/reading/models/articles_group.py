#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later


from collections.abc import Iterable
from typing import TYPE_CHECKING, Self

from django.db import models
from django.db.models.query import Prefetch
from slugify import slugify

from legadilo.reading import constants

from ...users.models import User
from .article import Article
from .tag import ArticlesGroupTag, Tag

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

else:
    TypedModelMeta = object


class ArticlesGroupQuerySet(models.QuerySet["ArticlesGroup"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)

    def for_search(self, searched_text: str) -> Self:
        return self.filter(
            models.Q(title__icontains=searched_text)
            | models.Q(description__icontains=searched_text)
            | models.Q(articles__title__icontains=searched_text)
            | models.Q(articles__summary__icontains=searched_text)
            | models.Q(tags__title__icontains=searched_text)
        )

    def with_metadata(self) -> Self:
        return self.annotate(
            annot_nb_articles_in_group=models.Count("articles", distinct=True),
            annot_unread_articles_count=models.Count(
                "articles", filter=models.Q(articles__is_read=False)
            ),
            annot_has_unread_articles=models.Case(
                models.When(annot_unread_articles_count__gt=0, then=models.Value(True)),  # noqa: FBT003 boolean-positional-value
                default=models.Value(False),  # noqa: FBT003 boolean-positional-value
                output_field=models.BooleanField(),
            ),
            annot_total_reading_time=models.Sum("articles__reading_time"),
        )

    def with_articles(self) -> Self:
        return self.prefetch_related(
            Prefetch(
                "articles",
                to_attr="sorted_articles",
                queryset=Article.objects.all().order_by("group_order"),
            )
        )

    def for_details(self, user: User) -> Self:
        return self.with_metadata().with_articles().for_user(user)


class ArticlesGroupManager(models.Manager["ArticlesGroup"]):
    _hints: dict

    def get_queryset(self) -> ArticlesGroupQuerySet:
        return ArticlesGroupQuerySet(model=self.model, using=self._db, hints=self._hints)

    def create_with_tags(self, user: User, title: str, description: str, tags: list[Tag]):
        group = self.create(user=user, title=title, description=description, slug=slugify(title))
        ArticlesGroupTag.objects.associate_group_with_tags(group, tags)
        return group

    def list_for_admin(
        self, user: User, searched_text: str = "", tag_slugs: Iterable[str] = ()
    ) -> ArticlesGroupQuerySet:
        qs = (
            self
            .get_queryset()
            .prefetch_related("tags")
            .filter(user=user)
            .with_metadata()
            .with_articles()
        )
        if searched_text:
            qs = qs.for_search(searched_text)
        if tag_slugs:
            qs = qs.filter(tags__slug__in=tag_slugs)

        return qs.order_by("-annot_unread_articles_count", "created_at")


class ArticlesGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=constants.ARTICLES_GROUP_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=constants.ARTICLES_GROUP_TITLE_MAX_LENGTH, blank=True)

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="article_groups")

    objects = ArticlesGroupManager()

    class Meta(TypedModelMeta):
        ordering = ("created_at", "id")

    def __str__(self):
        return f"ArticleGroup(id={self.id}, title={self.title})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    def update_from_details(self, title: str, description: str):
        self.title = title
        self.description = description
