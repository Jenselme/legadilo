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

from .manage_tokens_views import delete_token_view, list_tokens_view
from .notifications_views import list_notifications_view
from .user_views import (
    user_detail_view,
    user_redirect_view,
    user_update_settings_view,
    user_update_view,
)

__all__ = [
    "delete_token_view",
    "list_notifications_view",
    "list_tokens_view",
    "user_detail_view",
    "user_redirect_view",
    "user_update_settings_view",
    "user_update_view",
]
