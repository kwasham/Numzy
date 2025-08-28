import datetime as dt

from app.utils.helpers import parse_iso_datetime


def test_parse_iso_datetime_lowercase_z():
    value = "2023-05-06T12:00:00z"
    result = parse_iso_datetime(value)
    assert result == dt.datetime(2023, 5, 6, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_parse_iso_datetime_invalid_returns_none():
    assert parse_iso_datetime("not-a-date") is None
