from django.contrib import admin

from legadilo.feeds.models.article import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    pass
