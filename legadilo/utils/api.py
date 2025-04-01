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
from collections.abc import Set
from typing import Any

from django.db import models
from django.db.models import Model
from ninja import Schema


class ApiError(Schema):
    detail: str


FIELD_UNSET: Any = object()


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
        if attr in excluded_fields or value is FIELD_UNSET:
            continue

        updated_attrs.append(attr)
        setattr(model, attr, value)

    model.save(update_fields=updated_attrs)

    if must_refresh:
        model.refresh_from_db(from_queryset=refresh_qs)
