from django.urls import path

from . import views

app_name = "feeds"

urlpatterns = [
    path("", views.feeds_admin_view, name="feeds_admin"),
    path("subscribe/", views.subscribe_to_feed_view, name="subscribe_to_feed"),
    path(
        "articles/<int:feed_id>-<slug:feed_slug>/",
        views.feed_articles_view,
        name="feed_articles",
    ),
    path("articles/<int:feed_id>/", views.feed_articles_view, name="feed_articles"),
]
