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

import json
from typing import Any

from django.db import models
from pydantic import BaseModel as BaseSchema

from legadilo.utils.collections_utils import CustomJsonEncoder


class AnyOfType:
    def __init__(self, expected_type: Any):
        if not isinstance(expected_type, type):
            expected_type = type(expected_type)

        self.expected_type = expected_type

    def __eq__(self, other):
        return isinstance(other, self.expected_type)

    def __hash__(self):
        return hash(self.expected_type)


def serialize_for_snapshot(value: Any) -> str:
    if isinstance(value, BaseSchema):
        value = value.model_dump(mode="json")
    elif isinstance(value, list | tuple) and len(value) > 0 and isinstance(value[0], BaseSchema):
        value = [item.model_dump(mode="json") for item in value]

    value = json.dumps(value, indent=2, sort_keys=True, cls=CustomJsonEncoder)

    return str(value) + "\n"


def all_model_fields_except(model: type[models.Model], excluded_fields: set[str]):
    return [field.name for field in model._meta.fields if field.name not in excluded_fields]
