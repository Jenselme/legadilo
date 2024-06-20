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
from django.db.models import JSONField

from legadilo.core.forms.widgets import PrettyJSONWidget
from legadilo.reading.models import (
    Article,
    ArticleFetchError,
    ArticleTag,
    ReadingList,
    ReadingListTag,
    Tag,
)


class ArticleTagInline(admin.TabularInline):
    model = ArticleTag
    autocomplete_fields = ["tag"]


class ReadingListTagInline(admin.TabularInline):
    model = ReadingListTag
    autocomplete_fields = ["tag"]


class ArticleFetchErrorInline(admin.TabularInline):
    model = ArticleFetchError
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    search_fields = ["title", "initial_source_title", "link"]
    autocomplete_fields = ["user"]
    list_display = ["__str__", "obj_created_at", "obj_updated_at"]
    list_filter = ["is_read", "is_favorite", "is_for_later", "initial_source_type"]
    inlines = [
        ArticleTagInline,
        ArticleFetchErrorInline,
    ]
    readonly_fields = ("obj_created_at", "obj_updated_at")


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [
        ReadingListTagInline,
    ]


@admin.register(ArticleFetchError)
class ArticleFetchErrorAdmin(admin.ModelAdmin):
    search_fields = ["article__title", "article__link"]
    readonly_fields = ("article",)
    list_display = ["__str__", "created_at"]
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}
