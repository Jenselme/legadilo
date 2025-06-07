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
