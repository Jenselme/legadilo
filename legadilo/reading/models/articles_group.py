#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from slugify import slugify

from legadilo.reading import constants

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class ArticlesGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=constants.ARTICLES_GROUP_MAX_LENGTH)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=constants.ARTICLES_GROUP_MAX_LENGTH, blank=True)

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="article_groups")

    class Meta(TypedModelMeta):
        ordering = ("created_at", "id")

    def __str__(self):
        return f"ArticleGroup(id={self.id}, title={self.title})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super().save(*args, **kwargs)
