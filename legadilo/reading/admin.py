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
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [
        ArticleTagInline,
        ArticleFetchErrorInline,
    ]


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    autocomplete_fields = ["user"]
    inlines = [
        ReadingListTagInline,
    ]


@admin.register(ArticleFetchError)
class ArticleFetchErrorAdmin(admin.ModelAdmin):
    search_fields = ["article__title"]
    readonly_fields = ("article",)
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}
