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

from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import ReadingList
from legadilo.utils.urls import validate_from_url


def get_js_cfg_from_reading_list(reading_list: ReadingList):
    return {
        "is_reading_on_scroll_enabled": reading_list.enable_reading_on_scroll,
        "auto_refresh_interval": reading_list.auto_refresh_interval,
        "articles_list_min_refresh_timeout": constants.ARTICLES_LIST_MIN_REFRESH_TIMEOUT,
    }


def get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("reading:default_reading_list")
    )
