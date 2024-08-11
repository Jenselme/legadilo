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

from __future__ import annotations

from collections.abc import AsyncIterable, Iterable
from typing import TypeVar

T = TypeVar("T")


def min_or_none(collection: Iterable[T]) -> T | None:
    return _select_item_from_collection(min, collection)


def _select_item_from_collection(
    comparison_fn,
    collection: Iterable[T],
) -> T | None:
    comparable = [item for item in collection if item]
    if len(comparable) == 0:
        return None

    return comparison_fn(comparable)


def max_or_none(
    collection: Iterable[T],
) -> T | None:
    return _select_item_from_collection(max, collection)


async def alist(collection: AsyncIterable[T]) -> list[T]:
    output = []
    async for item in collection:
        output.append(item)

    return output
