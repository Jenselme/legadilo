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

from http import HTTPStatus
from json import JSONDecodeError

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import StreamingHttpResponse
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods
from pydantic import ValidationError as PydanticValidationError

from legadilo.import_export.services.exceptions import DataImportError
from legadilo.users.user_types import AuthenticatedHttpRequest

from ...utils.file import ensure_file_on_disk
from .. import constants
from ..services.custom_csv import import_custom_csv_file
from ..services.export import export_articles
from ..services.wallabag import import_wallabag_file


class ImportCustomCsvForm(forms.Form):
    csv_file = forms.FileField(
        required=True, widget=forms.ClearableFileInput(attrs={"accept": ".csv"})
    )


class ImportWallabagForm(forms.Form):
    wallabag_file = forms.FileField(
        required=True, widget=forms.ClearableFileInput(attrs={"accept": ".json"})
    )

    def clean_wallabag_file(self):
        if self.cleaned_data["wallabag_file"].size > constants.MAX_ARTICLES_FILE:
            raise ValidationError(
                _("The supplied file is too big to be imported"), code="file-too-big"
            )

        return self.cleaned_data["wallabag_file"]


@require_http_methods(["GET", "POST"])
@login_required
def import_export_articles_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    import_custom_csv_form = ImportCustomCsvForm()
    import_wallabag_form = ImportWallabagForm()
    status = HTTPStatus.OK

    if request.method == "POST":
        if "csv_file" in request.FILES:
            status, import_custom_csv_form = _import_custom_csv(request)
        elif "wallabag_file" in request.FILES:
            status, import_wallabag_form = _import_wallabag(request)
        else:
            status = HTTPStatus.BAD_REQUEST
            messages.error(request, _("This file type is not supported for imports."))

    return TemplateResponse(
        request,
        "import_export/import_export_articles.html",
        {
            "import_custom_csv_form": import_custom_csv_form,
            "import_wallabag_form": import_wallabag_form,
        },
        status=status,
    )


def _import_custom_csv(request: AuthenticatedHttpRequest):
    import_custom_csv_form = ImportCustomCsvForm(request.POST, request.FILES)
    status = HTTPStatus.OK
    if not import_custom_csv_form.is_valid():
        return status, import_custom_csv_form

    try:
        with ensure_file_on_disk(import_custom_csv_form.cleaned_data["csv_file"]) as file_path:
            (
                nb_imported_articles,
                nb_imported_feeds,
                nb_imported_categories,
            ) = import_custom_csv_file(request.user, file_path)
    except (DataImportError, UnicodeDecodeError, PydanticValidationError):
        status = HTTPStatus.BAD_REQUEST
        messages.error(request, _("The file you supplied is not valid."))
    else:
        # Reset form
        import_custom_csv_form = ImportCustomCsvForm()
        messages.success(
            request,
            _("Successfully imported %s feeds, %s feed categories and %s articles.")
            % (nb_imported_feeds, nb_imported_categories, nb_imported_articles),
        )

    return status, import_custom_csv_form


def _import_wallabag(request: AuthenticatedHttpRequest):
    import_wallabag_form = ImportWallabagForm(request.POST, request.FILES)
    status = HTTPStatus.OK
    if not import_wallabag_form.is_valid():
        return status, import_wallabag_form

    try:
        nb_imported_articles = import_wallabag_file(
            request.user, import_wallabag_form.cleaned_data["wallabag_file"]
        )
    except (JSONDecodeError, UnicodeDecodeError, PydanticValidationError):
        status = HTTPStatus.BAD_REQUEST
        messages.error(request, _("The file you supplied is not valid."))
    else:
        # Reset form
        import_wallabag_form = ImportWallabagForm()
        messages.success(request, _("Successfully imported %s articles") % nb_imported_articles)

    return status, import_wallabag_form


@require_GET
@login_required
def export_articles_view(request: AuthenticatedHttpRequest) -> StreamingHttpResponse:
    return StreamingHttpResponse(
        export_articles(request.user),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="articles.csv"'},
    )
