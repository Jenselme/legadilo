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

import csv

from legadilo.feeds.models import Feed, FeedCategory
from legadilo.import_export import constants
from legadilo.reading.models import Article
from legadilo.users.models import User
from legadilo.utils.text import ClearableStringIO
from legadilo.utils.time_utils import utcnow


def export_articles(user: User):
    buffer = ClearableStringIO()
    writer = csv.DictWriter(buffer, constants.CSV_HEADER_FIELDS)
    writer.writeheader()
    yield buffer.getvalue()

    feed_categories = FeedCategory.objects.export(user)
    writer.writerows(feed_categories)
    yield buffer.getvalue()
    feeds = Feed.objects.export(user)
    writer.writerows(feeds)
    yield buffer.getvalue()
    for articles_batch in Article.objects.export(user):
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
