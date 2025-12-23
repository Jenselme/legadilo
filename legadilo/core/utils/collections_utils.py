# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from collections.abc import Iterable
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from pydantic import BaseModel as BaseSchema

from legadilo.core.utils.types import DeletionResult


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
    """Merges deletion results into a single deletion result.

    Deletion results are tuples of (total_deleted, deleted_models) as returned by Django's delete().
    """
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
