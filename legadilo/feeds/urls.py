from django.urls import path, register_converter

from ..utils.urls import create_path_converter_from_enum
from . import constants, views

app_name = "feeds"

UpdateArticleActionsPathConverter = create_path_converter_from_enum(constants.UpdateArticleActions)
register_converter(UpdateArticleActionsPathConverter, "article_update_action")

urlpatterns = [
    path("reading/", views.reading_list_with_articles_view, name="default_reading_list"),
    path(
        "reading/lists/<slug:reading_list_slug>/",
        views.reading_list_with_articles_view,
        name="reading_list",
    ),
    path("reading/tags/<slug:tag_slug>/", views.tag_with_articles_view, name="tag_with_articles"),
    path(
        "reading/articles/<int:article_id>/<article_update_action:update_action>/",
        views.update_article_view,
        name="update_article",
    ),
    path("feeds/", views.subscribe_to_feed_view, name="subscribe_to_feed"),
]
