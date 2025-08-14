"""Miscellaneous helper functions."""

from __future__ import annotations

import datetime as dt
from typing import Optional


def parse_iso_datetime(value: str | None) -> Optional[dt.datetime]:
    """Parse an ISO8601 datetime string into a datetime object.

    Returns ``None`` if the value is falsy or cannot be parsed.
    """
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        return None