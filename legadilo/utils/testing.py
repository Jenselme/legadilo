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

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from django.db import models


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime | date):
            return obj.isoformat()

        if is_dataclass(obj):
            return asdict(obj)  # type: ignore[call-overload]

        return super().default(obj)


def serialize_for_snapshot(value: Any) -> str:
    value = json.dumps(value, indent=2, sort_keys=True, cls=CustomJsonEncoder)

    return str(value)


def all_model_fields_except(model: type[models.Model], excluded_fields: set[str]):
    return [field.name for field in model._meta.fields if field.name not in excluded_fields]
