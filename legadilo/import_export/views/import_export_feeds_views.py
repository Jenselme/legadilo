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

from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.feeds.models import Feed
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.time import utcnow


@require_GET
@login_required
def export_feeds_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    feeds_by_categories = Feed.objects.get_by_categories(request.user)
    feeds_without_category = feeds_by_categories.pop(None, [])

    return TemplateResponse(
        request,
        "import_export/export_feeds.opml",
        {
            "feeds_by_categories": feeds_by_categories,
            "feeds_without_category": feeds_without_category,
            "export_date": utcnow(),
        },
        content_type="text/x-opml",
    )
