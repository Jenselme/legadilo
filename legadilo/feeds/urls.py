# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
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
