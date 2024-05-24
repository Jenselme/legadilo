from django.contrib import admin

from legadilo.feeds.models import (
    Feed,
    FeedArticle,
    FeedCategory,
    FeedTag,
    FeedUpdate,
)


class FeedTagInline(admin.TabularInline):
    model = FeedTag
    autocomplete_fields = ["tag"]


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    search_fields = ["title", "category__title"]
    autocomplete_fields = ["user", "category"]
    list_filter = ["enabled", "feed_type"]
    inlines = [
        FeedTagInline,
    ]


@admin.register(FeedCategory)
class FeedCategoryAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]


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
