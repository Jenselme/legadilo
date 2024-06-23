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

import csv
from http import HTTPStatus

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.users.models import User
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.decorators import alogin_required

from ...feeds.models import Feed, FeedCategory
from ...reading.models import Article
from ...utils.text import ClearableStringIO
from .. import constants


class ImportCustomCsvForm(forms.Form):
    csv_file = forms.FileField(
        required=True, widget=forms.ClearableFileInput(attrs={"accept": ".csv"})
    )


@require_GET
@login_required
def import_export_articles_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    import_custom_csv_form = ImportCustomCsvForm()
    status = HTTPStatus.OK

    return TemplateResponse(
        request,
        "import_export/import_export_articles.html",
        {"form": import_custom_csv_form},
        status=status,
    )


@require_GET
@alogin_required
async def export_articles_view(request: AuthenticatedHttpRequest) -> StreamingHttpResponse:
    user = await request.auser()
    return StreamingHttpResponse(
        _export_articles(user),
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="articles.csv"'},
    )


async def _export_articles(user: User):
    buffer = ClearableStringIO()
    writer = csv.DictWriter(buffer, constants.CSV_HEADER_FIELDS)
    writer.writeheader()
    yield buffer.getvalue()

    feed_categories = await FeedCategory.objects.export(user)
    writer.writerows(feed_categories)
    yield buffer.getvalue()
    feeds = await Feed.objects.export(user)
    writer.writerows(feeds)
    yield buffer.getvalue()
    async for articles_batch in Article.objects.export(user):
        writer.writerows(articles_batch)
        yield buffer.getvalue()
