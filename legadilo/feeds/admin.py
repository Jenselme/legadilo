# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.contrib import admin
from django.core.management import call_command

from legadilo.feeds.models import (
    Feed,
    FeedArticle,
    FeedCategory,
    FeedTag,
    FeedUpdate,
)

logger = logging.getLogger(__name__)


class FeedTagInline(admin.TabularInline):
    model = FeedTag
    autocomplete_fields = ["tag"]


@admin.register(FeedUpdate)
class FeedUpdateAdmin(admin.ModelAdmin):
    search_fields = ["feed__title"]
    autocomplete_fields = ["feed"]
    list_display = ["__str__", "created_at"]
    list_filter = ["status"]


class FeedUpdateInline(admin.TabularInline):
    model = FeedUpdate
    readonly_fields = ("created_at",)
    fields = ("created_at", "status", "error_message", "feed_last_modified", "feed_etag")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    search_fields = ["title", "category__title", "feed_url", "site_url"]
    autocomplete_fields = ["user", "category"]
    list_filter = ["enabled", "feed_type"]
    list_display = ["__str__", "feed_url", "site_url", "created_at", "updated_at"]
    inlines = [
        FeedTagInline,
        FeedUpdateInline,
    ]
    actions = ["refresh_feeds", "force_refresh_feeds"]

    @admin.action(description="Refresh selected feeds")
    def refresh_feeds(self, request, queryset):
        logger.info("Refresh selected feeds from admin")
        call_command("update_feeds", "--feed-ids", *queryset.values_list("id", flat=True))
        logger.info(f"Refreshed {len(queryset)} feeds from admin")

    @admin.action(description="Force a refresh of selected feeds")
    def force_refresh_feeds(self, request, queryset):
        logger.info("Force refresh selected feeds from admin")
        call_command(
            "update_feeds",
            "--feed-ids",
            *queryset.values_list("id", flat=True),
            "--force",
        )
        logger.info(f"Refreshed {len(queryset)} feeds from admin")


@admin.register(FeedCategory)
class FeedCategoryAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]


@admin.register(FeedArticle)
class FeedArticleAdmin(admin.ModelAdmin):
    search_fields = ["feed__title", "article__title", "article__url"]
    autocomplete_fields = ["feed", "article"]
