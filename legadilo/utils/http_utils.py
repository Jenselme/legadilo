# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
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
