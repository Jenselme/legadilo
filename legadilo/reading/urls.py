from django.urls import path
from django.urls.converters import register_converter

from ..utils.urls import create_path_converter_from_enum
from . import constants, views

app_name = "reading"

UpdateArticleActionsPathConverter = create_path_converter_from_enum(constants.UpdateArticleActions)
register_converter(UpdateArticleActionsPathConverter, "article_update_action")

urlpatterns = [
    path("", views.reading_list_with_articles_view, name="default_reading_list"),
    path(
        "lists/<slug:reading_list_slug>/",
        views.reading_list_with_articles_view,
        name="reading_list",
    ),
    path("tags/<slug:tag_slug>/", views.tag_with_articles_view, name="tag_with_articles"),
    path(
        "articles/<int:article_id>-<slug:article_slug>/",
        views.article_details_view,
        name="article_details",
    ),
    path(
        "articles/<int:article_id>/<article_update_action:update_action>/",
        views.update_article_view,
        name="update_article",
    ),
    path("articles/add/", views.add_article_view, name="add_article"),
    path("articles/refetch/", views.refetch_article_view, name="refetch_article"),
    path("article/<int:article_id>/delete/", views.delete_article_view, name="delete_article"),
]
