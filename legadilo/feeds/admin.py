from django.contrib import admin

from legadilo.feeds.models import (
    Article,
    ArticleTag,
    Feed,
    FeedArticle,
    FeedCategory,
    FeedTag,
    FeedUpdate,
    ReadingList,
    ReadingListTag,
    Tag,
)


class ArticleTagInline(admin.TabularInline):
    model = ArticleTag
    autocomplete_fields = ["tag"]


class FeedTagInline(admin.TabularInline):
    model = FeedTag
    autocomplete_fields = ["tag"]


class ReadingListTagInline(admin.TabularInline):
    model = ReadingListTag
    autocomplete_fields = ["tag"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["user"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [
        ArticleTagInline,
    ]


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    search_fields = ["title", "category__name"]
    autocomplete_fields = ["user", "category"]
    list_filter = ["feed_type"]
    inlines = [
        FeedTagInline,
    ]


@admin.register(FeedCategory)
class FeedCategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["user"]


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["user"]
    inlines = [
        ReadingListTagInline,
    ]


@admin.register(FeedUpdate)
class FeedUpdateAdmin(admin.ModelAdmin):
    search_fields = ["feed__title"]
    autocomplete_fields = ["feed"]
    list_display = ["__str__", "created_at"]
    list_filter = ["status"]
    ordering = ["created_at"]


@admin.register(FeedArticle)
class FeedArticleAdmin(admin.ModelAdmin):
    search_fields = ["feed__title", "article__title"]
    autocomplete_fields = ["feed", "article"]
