"""Date discovery and arithmetic used by the physical-exam recency check."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_US_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

_LONG_FORM = re.compile(
    r"\b(" + "|".join(f"{m[:3]}(?:{m[3:]})?" for m in _MONTHS) + r")\.?\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE,
)


def _to_iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def find_date(text: str) -> str | None:
    """Extracts the first parseable date from a block of text, as YYYY-MM-DD."""
    iso = _ISO.search(text)
    if iso:
        parsed = _to_iso(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        if parsed:
            return parsed

    slash = _US_SLASH.search(text)
    if slash:
        parsed = _to_iso(int(slash.group(3)), int(slash.group(1)), int(slash.group(2)))
        if parsed:
            return parsed

    long_form = _LONG_FORM.search(text)
    if long_form:
        prefix = long_form.group(1).lower()[:3]
        month_index = next((i for i, m in enumerate(_MONTHS) if m.startswith(prefix)), None)
        if month_index is not None:
            parsed = _to_iso(int(long_form.group(3)), month_index + 1, int(long_form.group(2)))
            if parsed:
                return parsed

    return None


def days_between(from_iso: str, to_iso: str) -> int:
    """Whole days from ``from_iso`` to ``to_iso``. Negative when earlier."""
    return (date.fromisoformat(to_iso) - date.fromisoformat(from_iso)).days


def latest_date(dates: Iterable[str | None]) -> str | None:
    """Latest of a set of ISO dates, ignoring ``None``."""
    valid = sorted(d for d in dates if d is not None)
    return valid[-1] if valid else None
