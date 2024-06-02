from __future__ import annotations

from dateutil.relativedelta import relativedelta
from django.db import models

from legadilo.reading import constants
from legadilo.utils.time import utcnow


class ArticleFetchErrorQuerySet(models.QuerySet["ArticleFetchError"]):
    def for_cleanup(self):
        return self.filter(
            created_at__lt=utcnow() - relativedelta(days=constants.KEEP_ARTICLE_FETCH_ERROR_FOR)
        )


class ArticleFetchErrorManager(models.Manager["ArticleFetchError"]):
    _hints: dict

    def get_queryset(self) -> ArticleFetchErrorQuerySet:
        return ArticleFetchErrorQuerySet(model=self.model, using=self._db, hints=self._hints)


class ArticleFetchError(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    technical_debug_data = models.JSONField(blank=True, null=True)

    article = models.ForeignKey(
        "reading.Article", related_name="article_fetch_errors", on_delete=models.CASCADE
    )

    objects = ArticleFetchErrorManager()

    def __str__(self):
        return f"ArticleFetchError(article_link={self.article.link})"
