# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import URLPattern, path

from . import views

app_name = "import_export"

urlpatterns: list[URLPattern] = [
    path("feeds/export/", views.export_feeds_view, name="export_feeds"),
    path("feeds/import/", views.import_feeds_view, name="import_feeds"),
    path(
        "articles/import_export/", views.import_export_articles_view, name="import_export_articles"
    ),
    path("articles/export/", views.export_articles_view, name="export_articles"),
]
