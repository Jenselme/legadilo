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

from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "website"

urlpatterns = [
    path("", TemplateView.as_view(template_name="website/home.html"), name="home"),
    path("privacy/", TemplateView.as_view(template_name="website/privacy.html"), name="privacy"),
    path("manifest.json", views.manifest_view, name="manifest"),
    path("favicon.ico", views.default_favicon_view, name="favicon"),
]
