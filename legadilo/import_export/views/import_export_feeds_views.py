# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus
from xml.etree.ElementTree import (  # noqa: S405 etree methods are vulnerable to XML attacks
    ParseError as XmlParseError,
)

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.import_export.services.opml import import_opml_file
from legadilo.users.user_types import AuthenticatedHttpRequest

from .. import constants
from ..services.export import build_feeds_export_context


@require_GET
@login_required
def export_feeds_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "import_export/export_feeds.opml",
        build_feeds_export_context(request.user),
        content_type="text/x-opml",
    )


class ImportFeedsForm(forms.Form):
    opml_file = forms.FileField(
        required=True, widget=forms.ClearableFileInput(attrs={"accept": ".xml,.opml"})
    )

    def clean_opml_file(self):
        if self.cleaned_data["opml_file"].size > constants.MAX_SIZE_OPML_FILE:
            raise ValidationError(
                _("The supplied file is too big to be imported."), code="file-too-big"
            )

        return self.cleaned_data["opml_file"]


@require_http_methods(["GET", "POST"])
@login_required
def import_feeds_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    form = ImportFeedsForm()
    status = HTTPStatus.OK

    if request.method == "POST":
        form = ImportFeedsForm(request.POST, files=request.FILES)
        if form.is_valid():
            try:
                nb_imported_feeds, nb_imported_categories = import_opml_file(
                    request.user, form.cleaned_data["opml_file"]
                )
            except XmlParseError:
                status = HTTPStatus.BAD_REQUEST
                messages.error(request, _("The file you supplied is not valid."))
            else:
                # Reset form
                form = ImportFeedsForm()
                messages.success(
                    request,
                    _(
                        "Successfully imported %(nb_imported_feeds)s feeds into "
                        "%(nb_imported_categories)s categories."
                    )
                    % {
                        "nb_imported_feeds": nb_imported_feeds,
                        "nb_imported_categories": nb_imported_categories,
                    },
                )

    return TemplateResponse(
        request, "import_export/import_feeds.html", {"form": form}, status=status
    )
