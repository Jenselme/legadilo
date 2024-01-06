from datetime import UTC, datetime

from legadilo.utils.time import dt_to_http_date


def test_dt_to_http_date():
    dt = datetime(2023, 12, 31, 11, 23, tzinfo=UTC)

    http_date = dt_to_http_date(dt)

    assert http_date == "Sun, 31 Dec 2023 11:23:00 GMT"
