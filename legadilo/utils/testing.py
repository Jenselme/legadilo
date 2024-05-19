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
            return asdict(obj)

        return super().default(obj)


def serialize_for_snapshot(value: Any) -> str:
    value = json.dumps(value, indent=2, sort_keys=True, cls=CustomJsonEncoder)

    return str(value)


def all_model_fields_except(model: type[models.Model], excluded_fields: set[str]):
    return [field.name for field in model._meta.fields if field.name not in excluded_fields]
