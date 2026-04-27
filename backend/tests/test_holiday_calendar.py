# backend/tests/test_holiday_calendar.py
from datetime import date, time
from backend.holiday_calendar import is_nse_holiday, get_market_status

def test_republic_day_is_holiday():
    assert is_nse_holiday(date(2026, 1, 26)) is True

def test_regular_monday_is_not_holiday():
    assert is_nse_holiday(date(2026, 4, 13)) is False

def test_saturday_market_closed():
    status = get_market_status(date(2026, 4, 25), time(10, 0))
    assert status in ("closed", "futures_mode")

def test_weekday_market_open_hours():
    status = get_market_status(date(2026, 4, 28), time(10, 30))
    assert status == "open"

def test_weekday_pre_market():
    status = get_market_status(date(2026, 4, 28), time(9, 0))
    assert status == "pre_open"
