"""
tools/calendar_tool.py

Mock scheduling helper for medicine reminders and appointments.

No real notification system, calendar API, or background scheduler here
on purpose — for a mini project demo, computing and *displaying* the
next dose time on the dashboard demonstrates the concept just as well as
a real push notification would, without the added infra.
"""

from __future__ import annotations

from datetime import datetime, timedelta

_TIME_OF_DAY = {
    "morning": 8,
    "afternoon": 14,
    "evening": 18,
    "night": 21,
    "daily": 9,
}


def next_dose_times(frequency: str, now: datetime | None = None) -> list[datetime]:
    """Return the next occurrence(s) implied by a free-text frequency string.

    e.g. "morning, night" -> tomorrow-or-today at 08:00 and at 21:00.
    Unrecognized/empty frequency falls back to a single default 09:00 slot.
    """
    now = now or datetime.now()
    matched_hours = [hour for key, hour in _TIME_OF_DAY.items() if key in frequency.lower()]
    if not matched_hours:
        matched_hours = [9]

    results = []
    for hour in sorted(set(matched_hours)):
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        results.append(candidate)
    return results


def format_next_dose(frequency: str) -> str:
    """Human-readable "next dose" string for the UI, e.g. 'Tomorrow 08:00'."""
    times = next_dose_times(frequency)
    if not times:
        return "Not scheduled"
    parts = []
    for t in times:
        day = "Today" if t.date() == datetime.now().date() else "Tomorrow"
        parts.append(f"{day} {t.strftime('%H:%M')}")
    return ", ".join(parts)
