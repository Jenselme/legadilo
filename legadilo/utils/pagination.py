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
from typing import Any

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from ninja.pagination import LimitOffsetPagination as NinjaLimitOffsetPagination

from legadilo.utils.collections_utils import alist


def get_requested_page(paginator: Paginator, requested_page: int) -> Page:
    return (
        paginator.page(requested_page)
        if 1 <= requested_page <= paginator.num_pages
        else paginator.page(1)
    )


class LimitOffsetPagination(NinjaLimitOffsetPagination):
    """Custom paginator to fix a bug in Ninja pagination.

    There is a bug in Ninja when we try to paginate querysets in async context: we will get a
    SynchronousOnlyOperation error. This should be solved "soon" with
    https://github.com/vitalik/django-ninja/pull/1340
    """

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Any,
        **params: Any,
    ) -> Any:
        result = await super().apaginate_queryset(queryset, pagination, **params)
        result["items"] = await alist(result["items"])
        return result
