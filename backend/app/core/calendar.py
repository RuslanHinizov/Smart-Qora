"""One site calendar for event rollups, API queries and Telegram."""
import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def site_now():
    return datetime.now(ZoneInfo(os.environ.get("TZ", "Asia/Almaty")))


def site_day(instant=None):
    instant = instant or datetime.now(timezone.utc)
    return instant.astimezone(ZoneInfo(os.environ.get("TZ", "Asia/Almaty"))).date()


def day_bounds(day):
    zone = ZoneInfo(os.environ.get("TZ", "Asia/Almaty"))
    return (datetime.combine(day, time.min, zone).astimezone(timezone.utc),
            datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(timezone.utc))
