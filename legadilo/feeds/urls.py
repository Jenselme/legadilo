# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

from . import views

app_name = "feeds"

urlpatterns = [
    path("", views.feeds_admin_view, name="feeds_admin"),
    path("<int:feed_id>/", views.edit_feed_view, name="edit_feed"),
    path("subscribe/", views.subscribe_to_feed_view, name="subscribe_to_feed"),
    path("categories/", views.feed_category_admin_view, name="feed_category_admin"),
    path("categories/create/", views.create_feed_category_view, name="create_feed_category"),
    path(
        "categories/<int:category_id>/",
        views.edit_feed_category_view,
        name="edit_feed_category",
    ),
    path(
        "articles/<int:feed_id>-<slug:feed_slug>/",
        views.feed_articles_view,
        name="feed_articles",
    ),
    path("articles/<int:feed_id>/", views.feed_articles_view, name="feed_articles"),
]
