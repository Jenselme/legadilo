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

from typing import TYPE_CHECKING, Self

from django.db import models
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from legadilo.core.forms import FormChoices

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.users.models import User
else:
    TypedModelMeta = object


class FeedCategoryQuerySet(models.QuerySet["FeedCategory"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)


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


class FeedCategory(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    user = models.ForeignKey("users.User", related_name="feed_categories", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = FeedCategoryManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("slug", "user", name="%(app_label)s_%(class)s_unique"),
        ]
        ordering = ("title",)

    def __str__(self):
        return f"FeedCategory(id={self.id}, title={self.title}, user={self.user_id})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)
