# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.paginator import Page, Paginator


def get_requested_page(paginator: Paginator, requested_page: int) -> Page:
    return (
        paginator.page(requested_page)
        if 1 <= requested_page <= paginator.num_pages
        else paginator.page(1)
    )
