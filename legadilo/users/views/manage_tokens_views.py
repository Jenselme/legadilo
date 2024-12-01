# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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
from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from legadilo.core.forms.widgets import AutocompleteSelectWidget, DateTimeWidget
from legadilo.core.models import Timezone
from legadilo.users.models import ApplicationToken
from legadilo.users.user_types import AuthenticatedHttpRequest


class CreateTokenForm(forms.ModelForm):
    timezone = forms.ModelChoiceField(
        Timezone.objects.all(),
        required=False,
        widget=AutocompleteSelectWidget(),
        help_text=_("The timezone in which the validity end date should be understood."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["validity_end"].widget = DateTimeWidget()

    class Meta:
        model = ApplicationToken
        fields = ("title", "validity_end")

    def clean(self):
        super().clean()

        if self.cleaned_data["validity_end"] and self.cleaned_data["timezone"]:
            self.cleaned_data["validity_end"] = self.cleaned_data["validity_end"].replace(
                tzinfo=self.cleaned_data["timezone"].zone_info
            )


@login_required
@require_http_methods(["GET", "POST"])
def manage_tokens_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    form = CreateTokenForm(initial={"timezone": request.user.settings.timezone})
    new_application_token = None
    new_application_token_secret = None
    status = HTTPStatus.OK

    if request.method == "POST":
        form = CreateTokenForm(request.POST)
        if form.is_valid():
            new_application_token, new_application_token_secret, form, status = _create_token(
                request, form
            )
        else:
            status = HTTPStatus.BAD_REQUEST

    return TemplateResponse(
        request,
        "users/manage_tokens.html",
        {
            "new_application_token": new_application_token,
            "new_application_token_secret": new_application_token_secret,
            "tokens": ApplicationToken.objects.filter(user=request.user),
            "form": form,
        },
        status=status,
    )


def _create_token(
    request: AuthenticatedHttpRequest, form: CreateTokenForm
) -> tuple[ApplicationToken | None, str | None, CreateTokenForm, HTTPStatus]:
    status = HTTPStatus.OK

    try:
        new_application_token, new_application_token_secret = (
            ApplicationToken.objects.create_new_token(
                request.user, form.cleaned_data["title"], form.cleaned_data["validity_end"]
            )
        )
        form = CreateTokenForm(
            initial={
                "validity_end": form.cleaned_data["validity_end"].replace(tzinfo=None).isoformat()
                if form.cleaned_data["validity_end"]
                else "",
                "timezone": form.cleaned_data["timezone"],
            }
        )
    except IntegrityError:
        new_application_token = None
        new_application_token_secret = None
        status = HTTPStatus.CONFLICT
        messages.error(request, _("A token already exists with this name."))

    return new_application_token, new_application_token_secret, form, status


@login_required
@require_POST
def delete_token_view(request: AuthenticatedHttpRequest, token_id: int) -> HttpResponse:
    token = get_object_or_404(ApplicationToken, id=token_id, user=request.user)
    token.delete()

    return HttpResponse()
