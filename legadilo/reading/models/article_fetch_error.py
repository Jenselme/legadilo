# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from dateutil.relativedelta import relativedelta
from django.db import models

from legadilo.core.utils.time_utils import utcnow
from legadilo.core.utils.types import DeletionResult
from legadilo.reading import constants


class ArticleFetchErrorQuerySet(models.QuerySet["ArticleFetchError"]):
    def for_cleanup(self):
        return self.filter(
            created_at__lt=utcnow() - relativedelta(days=constants.KEEP_ARTICLE_FETCH_ERROR_FOR)
        )


class ArticleFetchErrorManager(models.Manager["ArticleFetchError"]):
    _hints: dict

    def get_queryset(self) -> ArticleFetchErrorQuerySet:
        return ArticleFetchErrorQuerySet(model=self.model, using=self._db, hints=self._hints)

    def cleanup_article_fetch_errors(self) -> DeletionResult:
        return self.get_queryset().for_cleanup().delete()


class ArticleFetchError(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    technical_debug_data = models.JSONField(blank=True, null=True)

    article = models.ForeignKey(
        "reading.Article", related_name="article_fetch_errors", on_delete=models.CASCADE
    )

    objects = ArticleFetchErrorManager()

    def __str__(self):
        return f"ArticleFetchError(article_url={self.article.url})"
