# backend/tests/test_alpha_vantage_client.py
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_daily_response(adjusted=True):
    key = "Time Series (Daily)" if adjusted else "Time Series FX (Daily)"
    close_key = "5. adjusted close" if adjusted else "4. close"
    data = {}
    for i in range(10):
        date_str = f"2024-0{(i % 9) + 1}-{(i + 1):02d}" if i < 9 else "2024-10-10"
        data[date_str] = {close_key: str(100.0 + i)}
    return {key: data}


def _make_global_quote(price="450.50", change_pct="1.23%"):
    return {
        "Global Quote": {
            "05. price": price,
            "10. change percent": change_pct,
        }
    }


def _make_fx_rate(rate="83.50"):
    return {
        "Realtime Currency Exchange Rate": {
            "5. Exchange Rate": rate,
        }
    }


# ── fetch_daily_series ────────────────────────────────────────────────────────

@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": "test_key"})
@patch("httpx.get")
def test_fetch_daily_series_returns_dataframe(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_daily_response(adjusted=True)
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from backend.alpha_vantage_client import fetch_daily_series
    df = fetch_daily_series("SPY", years=5)

    assert isinstance(df, pd.DataFrame)
    assert "close" in df.columns
    assert len(df) > 0


@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": ""})
def test_fetch_daily_series_no_key_returns_empty():
    from backend.alpha_vantage_client import fetch_daily_series
    df = fetch_daily_series("SPY")
    assert df.empty


@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": "test_key"})
@patch("httpx.get")
def test_fetch_daily_series_bad_response_returns_empty(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"Note": "API rate limit reached"}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from backend.alpha_vantage_client import fetch_daily_series
    df = fetch_daily_series("SPY")
    assert df.empty


# ── fetch_fx_daily ────────────────────────────────────────────────────────────

@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": "test_key"})
@patch("httpx.get")
def test_fetch_fx_daily_returns_dataframe(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_daily_response(adjusted=False)
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from backend.alpha_vantage_client import fetch_fx_daily
    df = fetch_fx_daily("USD", "INR", years=5)

    assert isinstance(df, pd.DataFrame)
    assert "close" in df.columns
    assert len(df) > 0


@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": ""})
def test_fetch_fx_daily_no_key_returns_empty():
    from backend.alpha_vantage_client import fetch_fx_daily
    df = fetch_fx_daily("USD", "INR")
    assert df.empty


# ── fetch_macro_snapshot ──────────────────────────────────────────────────────

@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": ""})
def test_fetch_macro_snapshot_no_key_returns_empty_dict():
    from backend.alpha_vantage_client import fetch_macro_snapshot
    result = fetch_macro_snapshot()
    assert result == {}


@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": "test_key"})
@patch("httpx.get")
def test_fetch_macro_snapshot_returns_full_snapshot(mock_get):
    responses = [
        _make_global_quote("450.50", "1.23%"),   # SPY
        _make_global_quote("380.20", "-0.55%"),   # QQQ
        _make_fx_rate("83.50"),                   # USD/INR
    ]
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        mock_resp = MagicMock()
        mock_resp.json.return_value = responses[call_count]
        mock_resp.raise_for_status = MagicMock()
        call_count += 1
        return mock_resp

    mock_get.side_effect = side_effect

    from backend.alpha_vantage_client import fetch_macro_snapshot
    result = fetch_macro_snapshot()

    assert result["source"] == "alpha_vantage"
    assert result["sp500"]["price"] == 450.50
    assert result["sp500"]["change_pct"] == pytest.approx(1.23)
    assert result["nasdaq"]["price"] == 380.20
    assert result["nasdaq"]["change_pct"] == pytest.approx(-0.55)
    assert result["usdinr"] == pytest.approx(83.50)
    assert "fetched_at" in result


@patch.dict("os.environ", {"ALPHA_VANTAGE_KEY": "test_key"})
@patch("httpx.get")
def test_fetch_macro_snapshot_partial_failure(mock_get):
    """Individual call failure should set that key to None but continue."""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("network error")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        if call_count == 2:
            mock_resp.json.return_value = _make_global_quote("380.20", "-0.55%")
        else:
            mock_resp.json.return_value = _make_fx_rate("83.50")
        return mock_resp

    mock_get.side_effect = side_effect

    from backend.alpha_vantage_client import fetch_macro_snapshot
    result = fetch_macro_snapshot()

    assert result["sp500"] is None          # failed call → None
    assert result["nasdaq"] is not None     # succeeded
    assert result["usdinr"] is not None     # succeeded
