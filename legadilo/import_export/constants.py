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

MAX_SIZE_OPML_FILE = 1024 * 1024  # 1MiB in bytes.
MAX_ARTICLES_FILE = 10 * 1024 * 1024  # 10MiB in bytes.
CSV_HEADER_FIELDS = (
    "category_id",
    "category_title",
    "feed_id",
    "feed_title",
    "feed_url",
    "feed_site_url",
    "article_id",
    "article_title",
    "article_url",
    "article_content",
    "article_date_published",
    "article_date_updated",
    "article_authors",
    "article_tags",
    "article_read_at",
    "article_is_favorite",
    "article_lang",
)
