from django.urls import path

from . import views

app_name = "feeds"

urlpatterns = [
    path("reading/", views.reading_list_with_articles_view, name="default_reading_list"),
    path(
        "reading/<slug:reading_list_slug>/",
        views.reading_list_with_articles_view,
        name="reading_list",
    ),
    path("feeds/", views.subscribe_to_feed_view, name="subscribe_to_feed"),
]
