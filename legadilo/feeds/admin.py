# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    search_fields = ["title", "category__title"]
    autocomplete_fields = ["user", "category"]
    list_filter = ["enabled", "feed_type"]
    inlines = [
        FeedTagInline,
        FeedUpdateInline,
    ]


@admin.register(FeedCategory)
class FeedCategoryAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]


@admin.register(FeedArticle)
class FeedArticleAdmin(admin.ModelAdmin):
    search_fields = ["feed__title", "article__title"]
    autocomplete_fields = ["feed", "article"]
