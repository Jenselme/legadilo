# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path
from django.urls.converters import register_converter

from legadilo.core.utils.urls import create_path_converter_from_enum

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
    path("tags/", views.tags_admin_view, name="tags_admin"),
    path("tags/create/", views.create_tag_view, name="create_tag"),
    path("tags/edit/<int:pk>/", views.edit_tag_view, name="edit_tag"),
    path("tags/<slug:tag_slug>/", views.tag_with_articles_view, name="tag_with_articles"),
    path(
        "tags/externals/list/",
        views.external_tag_with_articles_view,
        name="external_tag_with_articles",
    ),
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
    path("articles/<int:article_id>/delete/", views.delete_article_view, name="delete_article"),
    path(
        "articles/mark-as-read-in-bulk/",
        views.mark_articles_as_read_in_bulk_view,
        name="mark_articles_as_read_in_bulk",
    ),
    path("articles/add/", views.add_article_view, name="add_article"),
    path("articles/refetch/", views.refetch_article_view, name="refetch_article"),
    path(
        "articles-groups/<int:group_id>-<slug:group_slug>/",
        views.articles_group_details_view,
        name="articles_group_details",
    ),
    path("lists/", views.reading_list_admin_view, name="reading_lists_admin"),
    # To clearly differentiate from the view that list articles in list/<slug>.
    path("lists/edit/create/", views.reading_list_create_view, name="create_reading_list"),
    path(
        "lists/edit/<int:reading_list_id>/", views.reading_list_edit_view, name="edit_reading_list"
    ),
    path("search/", views.search_view, name="search"),
    path("comment/", views.create_comment_view, name="create_comment"),
    path("comment/<int:pk>/", views.display_comment_view, name="display_comment"),
    path("comment/<int:pk>/edit/", views.edit_comment_view, name="edit_comment"),
    path("comment/<int:pk>/delete/", views.delete_comment_view, name="delete_comment"),
]
