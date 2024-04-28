import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any


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
