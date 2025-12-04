# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections.abc import Callable, Set
from typing import Any

from django.db import models
from django.db.models import Model
from ninja import Schema
from pydantic_core import core_schema


class ApiError(Schema):
    detail: str


class NotSet:
    def __init__(self, example_value_factory: Callable[[], Any]):
        self._example_value_factory = example_value_factory

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.json_or_python_schema(
            json_schema=core_schema.none_schema(),
            python_schema=core_schema.none_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance._example_value_factory()
            ),
        )


def update_model_from_schema(
    model: Model,
    schema: Schema,
    *,
    must_refresh: bool = False,
    refresh_qs: models.QuerySet | None = None,
    excluded_fields: Set[str] = frozenset(),
):
    """Do a partial update of a model from a Ninja schema.

    Only fields set in the schema will be updated.
    """
    data = schema.model_dump(exclude_unset=True)
    updated_attrs = []

    for attr, value in data.items():
        if attr in excluded_fields or isinstance(value, NotSet):
            continue

        updated_attrs.append(attr)
        setattr(model, attr, value)

    model.save(update_fields=updated_attrs)

    if must_refresh:
        model.refresh_from_db(from_queryset=refresh_qs)
