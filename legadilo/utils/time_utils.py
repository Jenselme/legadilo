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
