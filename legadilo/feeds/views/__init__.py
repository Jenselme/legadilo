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

from .feed_articles_view import feed_articles_view
from .feed_categories_admin_views import (
    create_feed_category_view,
    edit_feed_category_view,
    feed_category_admin_view,
)
from .feeds_admin_view import edit_feed_view, feeds_admin_view
from .subscribe_to_feed_view import subscribe_to_feed_view

__all__ = [
    "create_feed_category_view",
    "edit_feed_category_view",
    "edit_feed_view",
    "feed_articles_view",
    "feed_category_admin_view",
    "feeds_admin_view",
    "subscribe_to_feed_view",
]
