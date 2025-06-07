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

from django import forms
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from legadilo.users.models import Notification
from legadilo.users.user_types import AuthenticatedHttpRequest


class ToggleNotificationStatusForm(forms.Form):
    notification_id = forms.IntegerField(required=False)


@login_required
@require_http_methods(["GET", "POST"])
def list_notifications_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    if request.method == "POST":
        form = ToggleNotificationStatusForm(request.POST)
        if form.is_valid() and "mark-as-unread" in request.POST:
            Notification.objects.mark_as_unread(request.user, form.cleaned_data["notification_id"])
        elif form.is_valid():
            Notification.objects.mark_as_read(request.user, form.cleaned_data["notification_id"])

    return TemplateResponse(
        request,
        "users/notifications.html",
        {"notifications": Notification.objects.list_recent_for_user(request.user)},
    )
