# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.paginator import Page, Paginator
from django.db import models


def get_requested_page(paginator: Paginator, requested_page: int) -> Page:
    return (
        paginator.page(requested_page)
        if 1 <= requested_page <= paginator.num_pages
        else paginator.page(1)
    )


def paginate_qs(qs: models.QuerySet, page_size: int = 500):
    paginator = Paginator(qs, page_size)
    for page_index in paginator.page_range:
        page = paginator.page(page_index)
        yield from page.object_list
