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
        "tags/externals/<str:tag>/",
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
    path("articles/add/", views.add_article_view, name="add_article"),
    path("articles/refetch/", views.refetch_article_view, name="refetch_article"),
    path("article/<int:article_id>/delete/", views.delete_article_view, name="delete_article"),
    path("lists/", views.reading_list_admin_view, name="reading_lists_admin"),
    path("list/create/", views.reading_list_create_view, name="create_reading_list"),
    # To clearly differentiate from the view that list articles.
    path(
        "list/edit/<int:reading_list_id>/", views.reading_list_edit_view, name="edit_reading_list"
    ),
]
