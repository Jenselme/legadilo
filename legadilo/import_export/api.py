#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Literal, assert_never

from django.http.response import StreamingHttpResponse
from django.template.response import TemplateResponse
from ninja import Query, Router
from ninja.schema import Schema
from pydantic import Field

from legadilo.feeds.api import OutFeedSchema
from legadilo.import_export.services.export import build_feeds_export_context, export_articles
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


class ExportArticlesQuery(Schema):
    include_feeds: bool = True
    updated_since: datetime | None = Field(
        default=None,
        description="Only include articles and feeds updated since the given date. "
        "Articles updated through a feed or manually or with a recent enough comment "
        "will be included. Feeds that has been fetched but not edited recently won't "
        "be included. Deleted articles are never returned by this endpoint, deleted "
        "articles are never included in any export.",
    )


@export_api_router.get(
    "/articles/", url_name="export_articles", summary="Export articles in CSV format"
)
def export_articles_view(
    request: AuthenticatedApiRequest, query: Query[ExportArticlesQuery]
) -> StreamingHttpResponse:
    return StreamingHttpResponse(
        export_articles(
            request.auth, include_feeds=query.include_feeds, updated_since=query.updated_since
        ),
        content_type="text/csv",
    )
