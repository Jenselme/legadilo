# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from django.db.models import JSONField

from legadilo.core.forms.widgets import PrettyJSONWidget
from legadilo.reading.models import (
    Article,
    ArticleFetchError,
    ArticlesGroup,
    ArticleTag,
    Comment,
    ReadingList,
    ReadingListTag,
    Tag,
)
from legadilo.reading.models.tag import SubTagMapping


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


class SubTagMappingInline(admin.TabularInline):
    model = SubTagMapping
    fk_name = "base_tag"
    autocomplete_fields = ["sub_tag"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [SubTagMappingInline]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    search_fields = ["title", "main_source_title", "url"]
    autocomplete_fields = ["user"]
    list_display = ["__str__", "obj_created_at", "obj_updated_at"]
    list_filter = ["is_read", "is_favorite", "is_for_later", "main_source_type"]
    inlines = [
        ArticleTagInline,
        ArticleFetchErrorInline,
    ]
    readonly_fields = ("obj_created_at", "obj_updated_at")
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    pass


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [
        ReadingListTagInline,
    ]


@admin.register(ArticleFetchError)
class ArticleFetchErrorAdmin(admin.ModelAdmin):
    search_fields = ["article__title", "article__url"]
    readonly_fields = ("article",)
    list_display = ["__str__", "created_at"]
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}


class ArticlesOfGroupInline(admin.TabularInline):
    model = Article

    fields = ("title", "url", "group_order")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("group_order")


@admin.register(ArticlesGroup)
class ArticlesGroupAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    list_display = ["__str__", "created_at"]
    inlines = [ArticlesOfGroupInline]
