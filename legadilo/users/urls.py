# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("~redirect/", view=views.user_redirect_view, name="redirect"),
    path("~update/", view=views.user_update_view, name="update"),
    path("~settings/", view=views.user_update_settings_view, name="update_settings"),
    path("<int:pk>/", view=views.user_detail_view, name="detail"),
    path("notifications/", views.list_notifications_view, name="list_notifications"),
    path("tokens/", views.manage_tokens_view, name="manage_tokens"),
    path("tokens/<int:token_id>/delete/", views.delete_token_view, name="delete_token"),
]
