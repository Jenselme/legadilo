# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
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
