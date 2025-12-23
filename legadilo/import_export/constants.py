# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

MAX_SIZE_OPML_FILE = 1024 * 1024  # 1MiB in bytes.
MAX_ARTICLES_FILE = 10 * 1024 * 1024  # 10MiB in bytes.
CSV_HEADER_FIELDS = (
    "group_id",
    "group_title",
    "group_description",
    "group_tags",
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
    "article_content_type",
    "article_date_published",
    "article_date_updated",
    "article_authors",
    "article_tags",
    "article_read_at",
    "article_is_favorite",
    "article_lang",
    "article_comments",
)
