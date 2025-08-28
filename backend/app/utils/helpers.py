"""Miscellaneous helper functions."""

from __future__ import annotations

import datetime as dt
from typing import Optional


def parse_iso_datetime(value: str | None) -> Optional[dt.datetime]:
    """Parse an ISO8601 datetime string into a :class:`datetime` object.

    The standard ``datetime.fromisoformat`` helper does not accept a lowercase
    ``z`` as the UTC designator. Some data sources provide timestamps that end
    with ``z`` instead of the canonical ``Z``. This function normalises that
    case and returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None
    try:
        if value.endswith("z"):
            value = value[:-1] + "Z"
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None
