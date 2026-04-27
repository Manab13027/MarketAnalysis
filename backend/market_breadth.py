"""Gainers / Losers for NIFTY 50, Bank NIFTY, Nifty Midcap 150, SENSEX."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import httpx

from backend.models import IndexMovers, StockMover

log = logging.getLogger(__name__)

# ── NSE constants ─────────────────────────────────────────────────────────────

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/live-equity-market",
}

NSE_INDEX_MAP: dict[str, str] = {
    "nifty50":   "NIFTY 50",
    "banknifty": "NIFTY BANK",
    "midcap":    "NIFTY MIDCAP 150",
}

SENSEX_COMPONENTS = [
    "RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO", "ICICIBANK.BO",
    "HINDUNILVR.BO", "ITC.BO", "SBIN.BO", "BHARTIARTL.BO", "KOTAKBANK.BO",
    "LT.BO", "AXISBANK.BO", "ASIANPAINT.BO", "MARUTI.BO", "ULTRACEMCO.BO",
    "TITAN.BO", "BAJFINANCE.BO", "NESTLEIND.BO", "WIPRO.BO", "HCLTECH.BO",
    "POWERGRID.BO", "SUNPHARMA.BO", "NTPC.BO", "TECHM.BO", "JSWSTEEL.BO",
    "TATAMOTORS.BO", "ONGC.BO", "TATASTEEL.BO", "M&M.BO", "BAJAJFINSV.BO",
]

CACHE_TTL = 60  # seconds

# ── Module-level state ────────────────────────────────────────────────────────

_nse_client: httpx.Client | None = None
_cache: dict[str, tuple[float, IndexMovers]] = {}  # key → (timestamp, data)


def _get_nse_client() -> httpx.Client:
    global _nse_client
    if _nse_client is None:
        _nse_client = httpx.Client(headers=NSE_HEADERS, timeout=10, follow_redirects=True)
        try:
            _nse_client.get("https://www.nseindia.com")
        except Exception as exc:
            log.warning("[market_breadth] NSE homepage warmup failed: %s", exc)
    return _nse_client


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mover(item: dict[str, Any]) -> StockMover:
    symbol = str(item.get("symbol", ""))
    price  = float(item.get("lastPrice", 0) or 0)
    change = float(item.get("change", 0) or 0)
    pct    = float(item.get("pChange", 0) or 0)
    return StockMover(
        symbol=symbol,
        name=str(item.get("meta", {}).get("companyName", symbol) if isinstance(item.get("meta"), dict) else symbol),
        price=round(price, 2),
        change=round(change, 2),
        change_pct=round(pct, 2),
    )


def _fetch_nse(index_key: str) -> IndexMovers:
    index_name = NSE_INDEX_MAP[index_key]
    client = _get_nse_client()
    url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_name}"
    resp = client.get(url)
    resp.raise_for_status()
    data: list[dict] = resp.json().get("data", [])
    # First item is the index itself — skip it
    stocks = [item for item in data[1:] if item.get("pChange") is not None]
    sorted_desc = sorted(stocks, key=lambda x: float(x.get("pChange", 0) or 0), reverse=True)
    sorted_asc  = sorted(stocks, key=lambda x: float(x.get("pChange", 0) or 0))
    return IndexMovers(
        index_key=index_key,
        gainers=[_make_mover(s) for s in sorted_desc[:5]],
        losers=[_make_mover(s) for s in sorted_asc[:5]],
        updated_at=datetime.now(),
    )


def _fetch_sensex() -> IndexMovers:
    import yfinance as yf
    df = yf.download(
        SENSEX_COMPONENTS,
        period="2d",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    close = df["Close"] if "Close" in df.columns else df.xs("Close", axis=1, level=0)
    if close.shape[0] < 2:
        return IndexMovers(index_key="sensex", gainers=[], losers=[], updated_at=datetime.now())

    prev_close = close.iloc[-2]
    last_close = close.iloc[-1]
    pct_changes = ((last_close - prev_close) / prev_close * 100).dropna()

    movers: list[StockMover] = []
    for sym, pct in pct_changes.items():
        price  = float(last_close[sym])
        change = float(last_close[sym] - prev_close[sym])
        movers.append(StockMover(
            symbol=str(sym).replace(".BO", ""),
            name=str(sym).replace(".BO", ""),
            price=round(price, 2),
            change=round(change, 2),
            change_pct=round(float(pct), 2),
        ))

    gainers = sorted(movers, key=lambda x: x.change_pct, reverse=True)[:5]
    losers  = sorted(movers, key=lambda x: x.change_pct)[:5]
    return IndexMovers(index_key="sensex", gainers=gainers, losers=losers, updated_at=datetime.now())


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_index_movers(index_key: str) -> IndexMovers:
    """Return top 5 gainers and losers for the given index (60-s cache)."""
    now = time.monotonic()
    cached = _cache.get(index_key)
    if cached and (now - cached[0]) < CACHE_TTL:
        return cached[1]

    try:
        if index_key == "sensex":
            result = _fetch_sensex()
        else:
            result = _fetch_nse(index_key)
        _cache[index_key] = (now, result)
        return result
    except Exception as exc:
        log.warning("[market_breadth] fetch failed for %s: %s", index_key, exc)
        # Return stale cache if available, else empty
        if cached:
            return cached[1]
        return IndexMovers(index_key=index_key, gainers=[], losers=[], updated_at=datetime.now())
