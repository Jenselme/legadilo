from django.db import models


class ArticleFetchError(models.Model):
    message = models.TextField()
    technical_debug_data = models.JSONField(blank=True, null=True)

    article = models.ForeignKey(
        "reading.Article", related_name="article_fetch_errors", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"ArticleFetchError(article_link={self.article.link})"
