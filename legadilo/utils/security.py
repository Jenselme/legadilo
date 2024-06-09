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

from collections.abc import Set

import nh3

ALLOWED_ATTRIBUTES = {
    **nh3.ALLOWED_ATTRIBUTES,
    "img": {"src", "alt"},
}


def full_sanitize(data: str) -> str:
    return nh3.clean(data, tags=set(), strip_comments=True)


def sanitize_keep_safe_tags(data: str, extra_tags_to_cleanup: Set[str] = frozenset()) -> str:
    allowed_tags = nh3.ALLOWED_TAGS - extra_tags_to_cleanup

    return nh3.clean(
        data,
        tags=allowed_tags,
        attributes=ALLOWED_ATTRIBUTES,
        strip_comments=True,
    )
