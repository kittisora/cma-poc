from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
_EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def arcgis_ms_to_local_date(ms: int | None) -> dt.date | None:
    """Convert an ArcGIS epoch-millisecond date to a calendar date in Fairfax County.

    The county stores sale dates as local midnight. About 1% of rows land at
    23:00 or 01:00 local time because of daylight-saving offsets, so the value is
    rounded to the nearest local midnight instead of truncated. Negative values
    (sales before 1970) are supported.
    """
    if ms is None:
        return None
    local = (_EPOCH + dt.timedelta(milliseconds=ms)).astimezone(EASTERN)
    return (local + dt.timedelta(hours=12)).date()


def months_between(earlier: dt.date, later: dt.date) -> float:
    return (later - earlier).days / 30.4375


def subtract_months(d: dt.date, months: int) -> dt.date:
    y, m = divmod((d.year * 12 + d.month - 1) - months, 12)
    m += 1
    last_day = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30,
                31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(y, m, min(d.day, last_day))


def today_local() -> dt.date:
    return dt.datetime.now(EASTERN).date()
