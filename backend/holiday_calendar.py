# backend/holiday_calendar.py
from datetime import date, time, datetime
from typing import Literal
import holidays

MarketStatusLiteral = Literal["open", "closed", "holiday", "futures_mode", "pre_open"]

NSE_OPEN  = time(9, 15)
NSE_CLOSE = time(15, 30)
PRE_OPEN_START = time(9, 0)

NSE_EXTRA_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 26),
    date(2026, 3, 31),
    date(2026, 4, 14),
    date(2026, 5, 1),
    date(2026, 8, 15),
    date(2026, 10, 2),
    date(2026, 11, 4),
    date(2026, 12, 25),
}

_in_holidays = holidays.India(years=range(2020, 2030))


def is_nse_holiday(d: date) -> bool:
    if d.weekday() >= 5:
        return True
    if d in _in_holidays or d in NSE_EXTRA_HOLIDAYS_2026:
        return True
    return False


def _is_weekday_holiday(d: date) -> bool:
    """True only for named holidays (not weekends)."""
    return d.weekday() < 5 and (d in _in_holidays or d in NSE_EXTRA_HOLIDAYS_2026)


def get_market_status(d: date, t: time) -> MarketStatusLiteral:
    if _is_weekday_holiday(d):
        return "holiday"
    if d.weekday() >= 5:   # weekend — futures still trade
        return "futures_mode"
    if t < PRE_OPEN_START:
        return "closed"
    if PRE_OPEN_START <= t < NSE_OPEN:
        return "pre_open"
    if NSE_OPEN <= t <= NSE_CLOSE:
        return "open"
    return "futures_mode"


def current_market_status() -> MarketStatusLiteral:
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    return get_market_status(now.date(), now.time())
