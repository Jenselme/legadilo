from django.db import models
from django.utils.translation import gettext_lazy as _

from legadilo.utils.validators import list_of_strings_json_schema_validator

from ..utils.feed_parsing import FeedArticle


class ArticleManager(models.Manager):
    async def update_or_create_from_articles_list(self, articles: list[FeedArticle], feed_id: int):
        for article_data in articles:
            await self.aupdate_or_create(
                feed_id=feed_id,
                article_feed_id=article_data.article_feed_id,
                defaults={
                    "title": article_data.title,
                    "summary": article_data.summary,
                    "content": article_data.content,
                    "authors": article_data.authors,
                    "contributors": article_data.contributors,
                    "tags": article_data.tags,
                    "link": article_data.link,
                    "published_at": article_data.published_at,
                    "updated_at": article_data.updated_at,
                },
            )


class Article(models.Model):
    title = models.CharField()
    summary = models.TextField()
    content = models.TextField()
    authors = models.JSONField(validators=[list_of_strings_json_schema_validator])
    contributors = models.JSONField(validators=[list_of_strings_json_schema_validator])
    tags = models.JSONField(validators=[list_of_strings_json_schema_validator])
    link = models.URLField()
    published_at = models.DateTimeField()
    article_feed_id = models.CharField(help_text=_("The id of the article in the feed."))

    is_read = models.BooleanField(default=False)

    feed = models.ForeignKey("feeds.Feed", related_name="articles", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArticleManager()

    class Meta:
        constraints = (
            models.UniqueConstraint("article_feed_id", "feed_id", name="feeds_Article_article_unique_in_feed"),
        )

    def __str__(self):
        return f"Article(feed_id={self.feed_id}, title={self.title})"
