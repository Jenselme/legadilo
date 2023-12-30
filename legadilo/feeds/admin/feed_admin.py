from django.contrib import admin

from legadilo.feeds.models.feed import Feed


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    pass
