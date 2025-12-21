#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later


from typing import TYPE_CHECKING

from django.db import models
from slugify import slugify

from legadilo.reading import constants

from ...users.models import User
from .tag import ArticlesGroupTag, Tag

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

else:
    TypedModelMeta = object


class ArticlesGroupQuerySet(models.QuerySet["ArticlesGroup"]):
    pass


class ArticlesGroupManager(models.Manager["ArticlesGroup"]):
    _hints: dict

    def get_queryset(self) -> ArticlesGroupQuerySet:
        return ArticlesGroupQuerySet(model=self.model, using=self._db, hints=self._hints)

    def create_with_tags(self, user: User, title: str, description: str, tags: list[Tag]):
        group = self.create(user=user, title=title, description=description, slug=slugify(title))
        ArticlesGroupTag.objects.associate_group_with_tags(group, tags)
        return group


class ArticlesGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=constants.ARTICLES_GROUP_MAX_LENGTH)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=constants.ARTICLES_GROUP_MAX_LENGTH, blank=True)

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="article_groups")

    objects = ArticlesGroupManager()

    class Meta(TypedModelMeta):
        ordering = ("created_at", "id")

    def __str__(self):
        return f"ArticleGroup(id={self.id}, title={self.title})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super().save(*args, **kwargs)
