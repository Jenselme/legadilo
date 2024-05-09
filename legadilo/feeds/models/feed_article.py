from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class FeedArticle(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="feed_articles", on_delete=models.CASCADE)
    article = models.ForeignKey(
        "reading.Article", related_name="feed_articles", on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "article", name="%(app_label)s_%(class)s_article_linked_once_per_feed"
            ),
        ]

    def __str__(self):
        return f"FeedArticle(feed={self.feed}, article={self.article})"
