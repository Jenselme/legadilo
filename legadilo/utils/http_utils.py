# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.http import QueryDict

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


def dict_to_query_dict(a_dict: dict) -> QueryDict:
    qs = urlencode(a_dict, doseq=True)
    return QueryDict(qs, mutable=False)
