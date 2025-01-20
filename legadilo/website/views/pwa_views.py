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

from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.views.decorators.http import require_GET


@require_GET
def manifest_view(request: HttpRequest) -> TemplateResponse:
    return TemplateResponse(
        request,
        "website/manifest.json",
        content_type="application/json",
        headers={"Cache-Control": f"max-age={24 * 60 * 60}, public"},
    )


@require_GET
def default_favicon_view(request: HttpRequest) -> HttpResponseRedirect:
    return HttpResponseRedirect(static("images/icons/legadilo.16x16.png"))
