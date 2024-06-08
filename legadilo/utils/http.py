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

import httpx

FETCH_TIMEOUT = 300


def get_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": "Legadilo"}, timeout=FETCH_TIMEOUT, follow_redirects=True
    )


def get_rss_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=5.0),
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Legadilo RSS"},
    )
