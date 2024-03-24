from datetime import UTC, datetime


def dt_to_http_date(dt: datetime) -> str:
    utc_dt = dt.astimezone(UTC)
    return utc_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def utcnow() -> datetime:
    return datetime.now(UTC)
