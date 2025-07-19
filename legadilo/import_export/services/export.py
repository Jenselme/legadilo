# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
from datetime import datetime

from legadilo.feeds.models import Feed, FeedCategory
from legadilo.import_export import constants
from legadilo.reading.models import Article
from legadilo.users.models import User
from legadilo.utils.text import ClearableStringIO
from legadilo.utils.time_utils import utcnow


def export_articles(
    user: User, *, include_feeds: bool = True, updated_since: datetime | None = None
):
    buffer = ClearableStringIO()
    writer = csv.DictWriter(buffer, constants.CSV_HEADER_FIELDS)
    writer.writeheader()
    yield buffer.getvalue()

    if include_feeds:
        feed_categories = FeedCategory.objects.export(user, updated_since=updated_since)
        writer.writerows(feed_categories)
        yield buffer.getvalue()
        feeds = Feed.objects.export(user, updated_since=updated_since)
        writer.writerows(feeds)
        yield buffer.getvalue()

    for articles_batch in Article.objects.export(user, updated_since=updated_since):
        writer.writerows(articles_batch)
        yield buffer.getvalue()


def build_feeds_export_context(user: User):
    feeds_by_categories = Feed.objects.get_by_categories(user)
    feeds_without_category = feeds_by_categories.pop(None, [])

    return {
        "feeds_by_categories": feeds_by_categories,
        "feeds_without_category": feeds_without_category,
        "export_date": utcnow(),
    }
