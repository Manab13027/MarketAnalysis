# backend/alpha_vantage_client.py
"""
Alpha Vantage client — NOT used for live polling.
Usage:
  - Historical data for ML training (called once at startup/retrain)
  - Macro snapshot for LLM context (refreshed every 2 hours)

Free tier: 25 calls/day — budget carefully.
"""
import logging
import os
from datetime import datetime, timezone

import httpx
import pandas as pd

AV_BASE_URL = "https://www.alphavantage.co/query"
logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    return os.getenv("ALPHA_VANTAGE_KEY", "")


def fetch_daily_series(symbol: str, years: int = 5) -> pd.DataFrame:
    """
    Fetch daily adjusted close prices for an equity/ETF symbol.
    Returns DataFrame with DatetimeIndex and column 'close'.
    Returns empty DataFrame on any error.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("alpha_vantage: ALPHA_VANTAGE_KEY not set — skipping fetch_daily_series(%s)", symbol)
        return pd.DataFrame()

    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "outputsize": "full",
                "apikey": api_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        ts = data.get("Time Series (Daily)")
        if not ts:
            logger.warning("alpha_vantage: no 'Time Series (Daily)' in response for %s. Keys: %s", symbol, list(data.keys()))
            return pd.DataFrame()

        records = {
            pd.Timestamp(date): float(vals["5. adjusted close"])
            for date, vals in ts.items()
        }
        df = pd.DataFrame.from_dict(records, orient="index", columns=["close"])
        df.index.name = "date"
        df = df.dropna().sort_index()
        cutoff = df.index.max() - pd.Timedelta(days=years * 365)
        df = df[df.index >= cutoff]
        return df

    except Exception as exc:
        logger.warning("alpha_vantage: fetch_daily_series(%s) failed: %s", symbol, exc)
        return pd.DataFrame()


def fetch_fx_daily(from_symbol: str, to_symbol: str, years: int = 5) -> pd.DataFrame:
    """
    Fetch daily FX close prices.
    Returns DataFrame with DatetimeIndex and column 'close'.
    Returns empty DataFrame on any error.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("alpha_vantage: ALPHA_VANTAGE_KEY not set — skipping fetch_fx_daily(%s/%s)", from_symbol, to_symbol)
        return pd.DataFrame()

    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={
                "function": "FX_DAILY",
                "from_symbol": from_symbol,
                "to_symbol": to_symbol,
                "outputsize": "full",
                "apikey": api_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        ts = data.get("Time Series FX (Daily)")
        if not ts:
            logger.warning("alpha_vantage: no 'Time Series FX (Daily)' for %s/%s. Keys: %s", from_symbol, to_symbol, list(data.keys()))
            return pd.DataFrame()

        records = {
            pd.Timestamp(date): float(vals["4. close"])
            for date, vals in ts.items()
        }
        df = pd.DataFrame.from_dict(records, orient="index", columns=["close"])
        df.index.name = "date"
        df = df.dropna().sort_index()
        cutoff = df.index.max() - pd.Timedelta(days=years * 365)
        df = df[df.index >= cutoff]
        return df

    except Exception as exc:
        logger.warning("alpha_vantage: fetch_fx_daily(%s/%s) failed: %s", from_symbol, to_symbol, exc)
        return pd.DataFrame()


def fetch_macro_snapshot() -> dict:
    """
    Fetch a macro snapshot using 3 Alpha Vantage API calls:
      - GLOBAL_QUOTE for SPY  (S&P 500 proxy)
      - GLOBAL_QUOTE for QQQ  (NASDAQ proxy)
      - CURRENCY_EXCHANGE_RATE USD→INR

    Returns {} immediately if ALPHA_VANTAGE_KEY is not set.
    On individual call failure: includes that key with None value.
    """
    api_key = _get_api_key()
    if not api_key:
        return {}

    result: dict = {
        "sp500": None,
        "nasdaq": None,
        "usdinr": None,
        "source": "alpha_vantage",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    # S&P 500 proxy via SPY
    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={"function": "GLOBAL_QUOTE", "symbol": "SPY", "apikey": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        quote = resp.json().get("Global Quote", {})
        result["sp500"] = {
            "price": float(quote["05. price"]),
            "change_pct": float(quote["10. change percent"].rstrip("%")),
        }
    except Exception as exc:
        logger.warning("alpha_vantage: GLOBAL_QUOTE SPY failed: %s", exc)

    # NASDAQ proxy via QQQ
    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={"function": "GLOBAL_QUOTE", "symbol": "QQQ", "apikey": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        quote = resp.json().get("Global Quote", {})
        result["nasdaq"] = {
            "price": float(quote["05. price"]),
            "change_pct": float(quote["10. change percent"].rstrip("%")),
        }
    except Exception as exc:
        logger.warning("alpha_vantage: GLOBAL_QUOTE QQQ failed: %s", exc)

    # USD→INR exchange rate
    try:
        resp = httpx.get(
            AV_BASE_URL,
            params={
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": "USD",
                "to_currency": "INR",
                "apikey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        rate_data = resp.json().get("Realtime Currency Exchange Rate", {})
        result["usdinr"] = float(rate_data["5. Exchange Rate"])
    except Exception as exc:
        logger.warning("alpha_vantage: CURRENCY_EXCHANGE_RATE USD/INR failed: %s", exc)

    return result
