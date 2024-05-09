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

    def get_queryset(self) -> FeedCategoryQuerySet:
        return FeedCategoryQuerySet(model=self.model, using=self._db, hints=self._hints)

    def get_all_choices(self, user: User) -> FormChoices:
        choices = [("", str(_("None")))]
        choices.extend(self.get_queryset().for_user(user).values_list("slug", "name"))
        return choices

    def get_first_for_user(self, user: User, slug: str) -> FeedCategory | None:
        return self.get_queryset().filter(user=user, slug=slug).first()


class FeedCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    user = models.ForeignKey("users.User", related_name="feed_categories", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = FeedCategoryManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("slug", "user", name="%(app_label)s_%(class)s_unique"),
        ]
        ordering = ("name",)

    def __str__(self):
        return f"FeedCategory(id={self.id}, name={self.name}, user={self.user})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)
