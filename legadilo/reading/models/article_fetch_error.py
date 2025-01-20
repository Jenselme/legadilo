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

from __future__ import annotations

from dateutil.relativedelta import relativedelta
from django.db import models

from legadilo.reading import constants
from legadilo.utils.time_utils import utcnow


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
