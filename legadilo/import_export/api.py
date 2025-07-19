#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Literal, assert_never

from django.template.response import TemplateResponse
from ninja import Query, Router
from ninja.schema import Schema

from legadilo.feeds.api import OutFeedSchema
from legadilo.import_export.services.export import build_feeds_export_context
from legadilo.users.user_types import AuthenticatedApiRequest

export_api_router = Router(tags=["export"])


class ExportFeedsQuery(Schema):
    format: Literal["opml", "json"] = "opml"


@export_api_router.get("/feeds/", url_name="export_feeds", summary="Export feeds in OPML or JSON")
def export_feeds_view(
    request: AuthenticatedApiRequest, query: Query[ExportFeedsQuery]
) -> TemplateResponse | dict:
    feeds = build_feeds_export_context(request.auth)
    match query.format:
        case "opml":
            return TemplateResponse(
                request,
                "import_export/export_feeds.opml",
                feeds,
                content_type="text/x-opml",
            )
        case "json":
            return {
                "feeds_by_categories": {
                    category: [
                        OutFeedSchema.model_validate(feed, context={"request": request})
                        for feed in feeds
                    ]
                    for category, feeds in feeds["feeds_by_categories"].items()
                },
                "feeds_without_category": [
                    OutFeedSchema.model_validate(feed, context={"request": request})
                    for feed in feeds["feeds_without_category"]
                ],
                "export_date": feeds["export_date"],
            }
        case _:
            assert_never(query.format)
