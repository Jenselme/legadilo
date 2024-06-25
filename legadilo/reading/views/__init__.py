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

from .article_actions_views import (
    delete_article_view,
    update_article_view,
)
from .article_details_views import article_details_view
from .fetch_article_views import add_article_view, refetch_article_view
from .list_of_articles_views import (
    external_tag_with_articles_view,
    reading_list_with_articles_view,
    tag_with_articles_view,
)
from .manage_reading_lists_views import (
    reading_list_admin_view,
    reading_list_create_view,
    reading_list_edit_view,
)

__all__ = [
    "add_article_view",
    "article_details_view",
    "delete_article_view",
    "external_tag_with_articles_view",
    "reading_list_admin_view",
    "reading_list_create_view",
    "reading_list_edit_view",
    "reading_list_with_articles_view",
    "refetch_article_view",
    "tag_with_articles_view",
    "update_article_view",
]
