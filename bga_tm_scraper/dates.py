"""Reading the dates BGA shows on game history and table pages."""

from datetime import datetime, timedelta
from typing import Optional


def parse_slash_date(first: int, second: int, year: int, hour: int, minute: int,
                     now: Optional[datetime] = None) -> datetime:
    """
    The datetime for a date BGA wrote as "03/04/2026 at 13:08".

    BGA writes these month first: 03/04/2026 is March 4th. Checked against 13,819 indexed
    games: the month-first reading is never later than the day the game was indexed and
    agrees with the dates of neighbouring table ids, while the day-first reading put 3,206
    of them in the future.

    The day-first reading is used only when month-first is impossible (first > 12) or would
    put the game in the future and day-first would not.
    """
    now = now or datetime.now()
    latest = now + timedelta(days=1)

    def reading(month: int, day: int) -> Optional[datetime]:
        try:
            return datetime(year, month, day, hour, minute, 0)
        except ValueError:
            return None

    month_first = reading(first, second)
    day_first = reading(second, first)
    if month_first is None:
        if day_first is None:
            raise ValueError(f"{first:02d}/{second:02d}/{year} is not a date")
        return day_first
    if month_first > latest and day_first is not None and day_first <= latest:
        return day_first
    return month_first
