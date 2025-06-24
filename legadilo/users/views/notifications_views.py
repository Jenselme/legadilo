# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
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
