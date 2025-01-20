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

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class FeedArticleManager(models.Manager):
    pass


class FeedArticle(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_articles", on_delete=models.CASCADE)
    article = models.ForeignKey(
        "reading.Article", related_name="feed_articles", on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FeedArticleManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "article", name="%(app_label)s_%(class)s_article_linked_once_per_feed"
            ),
        ]

    def __str__(self):
        return f"FeedArticle(feed={self.feed}, article={self.article})"
