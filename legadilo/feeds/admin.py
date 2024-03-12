from django.contrib import admin

from legadilo.feeds.models.article import Article
from legadilo.feeds.models.feed import Feed


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    pass


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    pass
