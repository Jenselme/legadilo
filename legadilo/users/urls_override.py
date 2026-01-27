#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from django.urls import path

from legadilo.users import views

urlpatterns = [
    path("~signup/", views.signup_view, name="account_signup"),
]
