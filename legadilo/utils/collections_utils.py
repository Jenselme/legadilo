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

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from pydantic import BaseModel as BaseSchema

from legadilo.types import DeletionResult


class CustomJsonEncoder(DjangoJSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, BaseSchema):
            return o.model_dump(mode="json")

        return super().default(o)


def min_or_none[T](collection: Iterable[T]) -> T | None:
    return _select_item_from_collection(min, collection)


def _select_item_from_collection[T](
    comparison_fn,
    collection: Iterable[T],
) -> T | None:
    comparable = [item for item in collection if item]
    if len(comparable) == 0:
        return None

    return comparison_fn(comparable)


def max_or_none[T](
    collection: Iterable[T],
) -> T | None:
    return _select_item_from_collection(max, collection)


def merge_deletion_results(deletion_results: Iterable[DeletionResult]) -> DeletionResult:
    total_deleted = 0
    deleted_models: dict[str, int] = {}

    for deletion_result in deletion_results:
        total_deleted += deletion_result[0]
        all_impacted_models = set(deleted_models.keys()) | set(deletion_result[1].keys())
        for model in all_impacted_models:
            if model in deleted_models:
                deleted_models[model] += deletion_result[1].get(model, 0)
            else:
                deleted_models[model] = deletion_result[1][model]

    return total_deleted, deleted_models
