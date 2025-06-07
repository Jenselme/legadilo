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

import httpx
from django.conf import settings

from legadilo import constants


def get_sync_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": "Legadilo"},
        timeout=settings.ARTICLE_FETCH_TIMEOUT,
        follow_redirects=True,
    )


def get_rss_sync_client() -> httpx.Client:
    return httpx.Client(
        limits=httpx.Limits(
            max_connections=constants.MAX_PARALLEL_CONNECTIONS,
            max_keepalive_connections=constants.MAX_PARALLEL_CONNECTIONS,
            keepalive_expiry=5.0,
        ),
        timeout=settings.RSS_FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Legadilo RSS"},
    )
