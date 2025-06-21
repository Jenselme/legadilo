# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime
from typing import Any

from dateutil.parser import ParserError
from dateutil.parser import parse as datetime_parse


def dt_to_http_date(dt: datetime) -> str:
    utc_dt = dt.astimezone(UTC)
    return utc_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def utcnow() -> datetime:
    return datetime.now(UTC)


def utcdt(  # noqa: PLR0913,PLR0917 (too many arguments)
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=UTC)


def safe_datetime_parse(data: Any) -> datetime | None:
    if not data:
        return None

    try:
        return datetime_parse(data).astimezone(UTC)
    except (ParserError, OverflowError):
        return None
