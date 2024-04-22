from datetime import UTC, datetime

import pytest

from legadilo.utils.time import dt_to_http_date, safe_datetime_parse, utcdt


def test_dt_to_http_date():
    dt = datetime(2023, 12, 31, 11, 23, tzinfo=UTC)

    http_date = dt_to_http_date(dt)

    assert http_date == "Sun, 31 Dec 2023 11:23:00 GMT"


@pytest.mark.parametrize(
    ("data", "expected_datetime"),
    [
        pytest.param("2024-02-27 00:00:00+01:00", utcdt(2024, 2, 26, hour=23), id="valid-datetime"),
        pytest.param("hello", None, id="trash"),
    ],
)
def test_safe_datetime_parse(data: str, expected_datetime: datetime | None):
    datetime = safe_datetime_parse(data)

    assert datetime == expected_datetime
