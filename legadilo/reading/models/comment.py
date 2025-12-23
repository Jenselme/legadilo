# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class Comment(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    text = models.TextField()

    article = models.ForeignKey(
        "reading.Article", related_name="comments", on_delete=models.CASCADE
    )

    class Meta(TypedModelMeta):
        ordering = ("created_at", "id")

    def __str__(self):
        return f"Comment(article={self.article.title}, text={self.text[:50]})"
