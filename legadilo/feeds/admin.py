from django.contrib import admin

from legadilo.feeds.models.article import Article
from legadilo.feeds.models.feed import Feed
from legadilo.feeds.models.reading_list import ReadingList


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    pass


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    pass


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    pass
