# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from legadilo.types import FormChoices

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.users.models import User
else:
    TypedModelMeta = object


class FeedCategoryQuerySet(models.QuerySet["FeedCategory"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)

    def for_export(self, user: User):
        return self.for_user(user).order_by("id")


class FeedCategoryManager(models.Manager["FeedCategory"]):
    _hints: dict

    def create(self, **kwargs):
        kwargs.setdefault("slug", slugify(kwargs["title"]))
        return super().create(**kwargs)

    def get_queryset(self) -> FeedCategoryQuerySet:
        return FeedCategoryQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_all_choices(self, user: User) -> FormChoices:
        choices = [("", str(_("None")))]
        choices.extend(self.get_queryset().for_user(user).values_list("slug", "title"))
        return choices

    def get_first_for_user(self, user: User, slug: str) -> FeedCategory | None:
        return self.get_queryset().filter(user=user, slug=slug).first()

    def export(self, user: User) -> list[dict[str, Any]]:
        feed_categories = []
        for feed_category in self.get_queryset().for_export(user):
            feed_categories.append({
                "category_id": feed_category.id,
                "category_title": feed_category.title,
                "feed_id": "",
                "feed_title": "",
                "feed_url": "",
                "feed_site_url": "",
                "article_id": "",
                "article_title": "",
                "article_url": "",
                "article_content": "",
                "article_date_published": "",
                "article_date_updated": "",
                "article_authors": "",
                "article_tags": "",
                "article_read_at": "",
                "article_is_favorite": "",
                "article_lang": "",
            })

        return feed_categories


class FeedCategory(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    user = models.ForeignKey("users.User", related_name="feed_categories", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FeedCategoryManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("slug", "user", name="%(app_label)s_%(class)s_unique"),
        ]
        ordering = ("title",)

    def __str__(self):
        return f"FeedCategory(id={self.id}, title={self.title}, user={self.user_id})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        return super().save(*args, **kwargs)
