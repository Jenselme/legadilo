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
