from django.contrib import admin

from legadilo.feeds.models import (
    Article,
    ArticleTag,
    Feed,
    FeedTag,
    ReadingList,
    ReadingListTag,
    Tag,
)


class ArticleTagInline(admin.TabularInline):
    model = ArticleTag


class FeedTagInline(admin.TabularInline):
    model = FeedTag


class ReadingListTagInline(admin.TabularInline):
    model = ReadingListTag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [
        ArticleTagInline,
    ]


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    inlines = [
        FeedTagInline,
    ]


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    inlines = [
        ReadingListTagInline,
    ]
