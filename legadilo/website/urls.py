# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
