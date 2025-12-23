# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from .article_actions_views import (
    mark_articles_as_read_in_bulk_view,
    update_article_view,
)
from .article_details_views import article_details_view
from .articles_group_views import (
    article_groups_read_all_articles_view,
    articles_group_details_view,
    articles_groups_list_view,
)
from .comment_views import (
    create_comment_view,
    delete_comment_view,
    display_comment_view,
    edit_comment_view,
)
from .delete_article_view import delete_article_view
from .fetch_article_views import add_article_view, refetch_article_view
from .list_of_articles_views import (
    external_tag_with_articles_view,
    reading_list_with_articles_view,
    tag_with_articles_view,
)
from .reading_lists_admin_views import (
    reading_list_admin_view,
    reading_list_create_view,
    reading_list_edit_view,
)
from .search_views import search_view
from .tags_admin_views import create_tag_view, edit_tag_view, tags_admin_view

__all__ = [
    "add_article_view",
    "article_details_view",
    "article_groups_read_all_articles_view",
    "articles_group_details_view",
    "articles_groups_list_view",
    "create_comment_view",
    "create_tag_view",
    "delete_article_view",
    "delete_comment_view",
    "display_comment_view",
    "edit_comment_view",
    "edit_tag_view",
    "external_tag_with_articles_view",
    "mark_articles_as_read_in_bulk_view",
    "reading_list_admin_view",
    "reading_list_create_view",
    "reading_list_edit_view",
    "reading_list_with_articles_view",
    "refetch_article_view",
    "search_view",
    "tag_with_articles_view",
    "tags_admin_view",
    "update_article_view",
]
