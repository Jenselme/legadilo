# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import reverse

from legadilo.core.utils.urls import validate_from_url
from legadilo.reading.models import ReadingList


def get_js_cfg_from_reading_list(reading_list: ReadingList):
    return {
        "is_reading_on_scroll_enabled": reading_list.enable_reading_on_scroll,
        "auto_refresh_interval": reading_list.auto_refresh_interval,
    }


def get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("reading:default_reading_list")
    )
