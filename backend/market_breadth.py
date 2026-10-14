"""Gainers / Losers for NIFTY 50, Bank NIFTY, Nifty Midcap 150, SENSEX."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import httpx

from backend.models import FIIDIIEntry, FuturesContract, IndexMovers, StockMover

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
    "500570.BO", "ONGC.BO", "TATASTEEL.BO", "M&M.BO", "BAJAJFINSV.BO",
]

CACHE_TTL = 60  # seconds

# ── Module-level state ────────────────────────────────────────────────────────

_nse_client: httpx.Client | None = None
_cache: dict[str, tuple[float, IndexMovers]] = {}
_futures_cache: tuple[float, list[FuturesContract]] = (0.0, [])
_fiidii_cache: tuple[float, list[FIIDIIEntry]] = (0.0, [])  # key → (timestamp, data)


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


# ── NIFTY + GIFT NIFTY Futures ────────────────────────────────────────────────

def _parse_futures(symbol: str, is_gift: bool = False) -> list[FuturesContract]:
    """Fetch futures contracts from NSE derivatives API for a given symbol."""
    client = _get_nse_client()
    url    = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
    resp   = client.get(url)
    resp.raise_for_status()
    stocks = resp.json().get("stocks", [])

    contracts: list[FuturesContract] = []
    for item in stocks:
        meta = item.get("metadata", {})
        if meta.get("instrumentType") != "Index Futures":
            continue
        expiry     = meta.get("expiryDate", "")
        price      = float(meta.get("lastPrice", 0) or 0)
        change     = float(meta.get("change", 0) or 0)
        change_pct = float(meta.get("pChange", 0) or 0)
        oi         = float(meta.get("openInterest", 0) or 0)
        # Short label: "NIFTY Apr" or "GIFT May"
        try:
            from datetime import datetime as _dt
            exp_dt  = _dt.strptime(expiry, "%d-%b-%Y")
            mon_str = exp_dt.strftime("%b %Y")
        except Exception:
            mon_str = expiry
        prefix = "GIFT NIFTY" if is_gift else "NIFTY"
        contracts.append(FuturesContract(
            label=f"{prefix} {mon_str}",
            expiry=expiry,
            price=round(price, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 3),
            oi=oi if oi else None,
            is_gift=is_gift,
        ))
    # Sort by expiry date, keep max 3 months
    contracts.sort(key=lambda c: c.expiry)
    return contracts[:3]


def _fetch_bhav_futures() -> list[FuturesContract]:
    """
    Fallback: parse NIFTY index futures from NSE F&O bhav copy (prev close).
    Tries today, then walks back up to 5 trading days.
    Returns [] if unavailable.
    """
    import datetime as _dt, io, zipfile, csv as _csv
    today = _dt.date.today()
    for delta in range(5):
        d = today - _dt.timedelta(days=delta)
        if d.weekday() >= 5:        # skip Saturday/Sunday
            continue
        ds  = d.strftime("%Y%m%d")
        url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ds}_F_0000.csv.zip"
        try:
            r = httpx.get(url, headers=NSE_HEADERS, timeout=15, follow_redirects=True)
            if r.status_code != 200 or len(r.content) < 5000:
                continue
            z       = zipfile.ZipFile(io.BytesIO(r.content))
            content = z.read(z.namelist()[0]).decode("utf-8")
            reader  = _csv.DictReader(io.StringIO(content))
            contracts: list[FuturesContract] = []
            for row in reader:
                sym  = row.get("TckrSymb", "")
                ftype = row.get("FinInstrmTp", "")
                if sym not in ("NIFTY", "GIFTNIFTY") or ftype != "IDF":
                    continue
                is_gift    = sym == "GIFTNIFTY"
                expiry_raw  = row.get("XpryDt", "")
                close_price = float(row.get("ClsPric") or 0)
                prev_close  = float(row.get("PrvsClsgPric") or close_price)
                if close_price == 0:
                    continue
                change     = round(close_price - prev_close, 2)
                change_pct = round((change / prev_close * 100) if prev_close else 0, 3)
                try:
                    exp_dt  = _dt.date.fromisoformat(expiry_raw)
                    mon_str = exp_dt.strftime("%b %Y")
                    expiry  = exp_dt.strftime("%d-%b-%Y")
                except Exception:
                    mon_str = expiry_raw
                    expiry  = expiry_raw
                prefix = "GIFT NIFTY" if is_gift else "NIFTY"
                contracts.append(FuturesContract(
                    label=f"{prefix} {mon_str}",
                    expiry=expiry,
                    price=round(close_price, 2),
                    change=change,
                    change_pct=change_pct,
                    oi=None,
                    is_gift=is_gift,
                    is_prev_close=True,
                ))
            contracts.sort(key=lambda c: c.expiry)
            if contracts:
                log.info("[market_breadth] bhav fallback loaded %d futures (%s)", len(contracts), ds)
                # Return up to 1 GIFT + 3 NIFTY
                gift   = [c for c in contracts if c.is_gift][:1]
                nifty  = [c for c in contracts if not c.is_gift][:3]
                return gift + nifty
        except Exception as exc:
            log.debug("[market_breadth] bhav fallback %s failed: %s", ds, exc)
    return []


def fetch_nifty_futures() -> list[FuturesContract]:
    """
    Return GIFT NIFTY (near month) + NIFTY 50 (3 monthly) futures. 60-s cache.
    Falls back to bhav copy (prev close) when the derivative API is empty (market closed).
    """
    global _futures_cache
    now = time.monotonic()
    if now - _futures_cache[0] < CACHE_TTL:
        return _futures_cache[1]

    result: list[FuturesContract] = []

    # GIFT NIFTY — only available during market hours via NSE derivative API
    try:
        gift = _parse_futures("GIFTNIFTY", is_gift=True)
        result.extend(gift)
    except Exception as exc:
        log.warning("[market_breadth] GIFT NIFTY fetch failed: %s", exc)

    # NIFTY 50 futures — 3 monthly expiries (live)
    nifty_live: list[FuturesContract] = []
    try:
        nifty_live = _parse_futures("NIFTY", is_gift=False)
        result.extend(nifty_live)
    except Exception as exc:
        log.warning("[market_breadth] NIFTY futures fetch failed: %s", exc)

    # Fallback: if live API returned nothing, use bhav copy prev-close data
    if not nifty_live:
        try:
            bhav = _fetch_bhav_futures()
            result.extend(bhav)
        except Exception as exc:
            log.warning("[market_breadth] bhav futures fallback failed: %s", exc)

    if result:
        _futures_cache = (now, result)
    elif _futures_cache[1]:
        # Keep stale cache rather than showing nothing
        return _futures_cache[1]
    return result


# ── FII / DII ─────────────────────────────────────────────────────────────────

FII_DII_TTL = 300  # refresh every 5 minutes


def _fetch_participant_oi() -> dict[str, dict]:
    """
    Parse NSE's participant-wise OI CSV.
    Returns dict keyed by participant type: "FII", "DII", "Client", "Pro"
    Each value: {fut_idx_long, fut_idx_short, opt_idx_long, opt_idx_short,
                 fut_stk_long, fut_stk_short, total_long, total_short}
    """
    import datetime as _dt, csv, io
    client = _get_nse_client()
    ddmmyyyy = _dt.date.today().strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv"
    # Use a fresh client for archives (different SSL config)
    r = httpx.get(url, headers=NSE_HEADERS, timeout=10, follow_redirects=True)
    r.raise_for_status()
    lines = r.text.strip().split("\n")
    # Row 1 = header, rows 2-5 = data
    result: dict[str, dict] = {}
    for line in lines[2:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 15:
            continue
        key = parts[0].strip().strip('"')  # "FII", "DII", "Client", "Pro"
        if key not in ("FII", "DII", "Client", "Pro"):
            continue
        def _i(idx: int) -> int:
            try: return int(parts[idx].replace(",", "").strip() or 0)
            except: return 0
        result[key] = {
            "fut_idx_long":  _i(1),
            "fut_idx_short": _i(2),
            "fut_stk_long":  _i(3),
            "fut_stk_short": _i(4),
            # Opt index: Call Long(5) + Put Long(6) / Call Short(7) + Put Short(8)
            "opt_idx_long":  _i(5) + _i(6),
            "opt_idx_short": _i(7) + _i(8),
            "total_long":    _i(13),
            "total_short":   _i(14),
        }
    return result


def fetch_fii_dii() -> list[FIIDIIEntry]:
    """
    Fetch today's FII/DII data:
    - Cash market buy/sell from NSE fiidiiTradeReact API
    - F&O participant-wise OI from NSE archive CSV
    Cached 5 minutes.
    """
    global _fiidii_cache
    now = time.monotonic()
    if now - _fiidii_cache[0] < FII_DII_TTL and _fiidii_cache[1]:
        return _fiidii_cache[1]

    # ── Cash market ───────────────────────────────────────────────────────────
    cash: dict[str, dict] = {}
    try:
        client = _get_nse_client()
        r = client.get("https://www.nseindia.com/api/fiidiiTradeReact")
        r.raise_for_status()
        for item in r.json():
            cat = item["category"]  # "FII/FPI" or "DII"
            cash[cat] = {
                "date":       item.get("date", ""),
                "cash_buy":   float(item.get("buyValue",  0) or 0),
                "cash_sell":  float(item.get("sellValue", 0) or 0),
                "cash_net":   float(item.get("netValue",  0) or 0),
            }
    except Exception as exc:
        log.warning("[market_breadth] FII/DII cash fetch failed: %s", exc)

    # ── F&O participant OI CSV ────────────────────────────────────────────────
    oi: dict[str, dict] = {}
    try:
        oi = _fetch_participant_oi()
    except Exception as exc:
        log.warning("[market_breadth] participant OI CSV failed: %s", exc)

    # ── Merge ─────────────────────────────────────────────────────────────────
    rows: list[FIIDIIEntry] = []
    # Map: cash key → OI key
    for cash_key, oi_key in [("DII", "DII"), ("FII/FPI", "FII")]:
        c = cash.get(cash_key, {})
        o = oi.get(oi_key, {})
        if not c and not o:
            continue
        rows.append(FIIDIIEntry(
            category=cash_key,
            date=c.get("date", ""),
            cash_buy=c.get("cash_buy", 0.0),
            cash_sell=c.get("cash_sell", 0.0),
            cash_net=c.get("cash_net", 0.0),
            fut_idx_long=o.get("fut_idx_long"),
            fut_idx_short=o.get("fut_idx_short"),
            opt_idx_long=o.get("opt_idx_long"),
            opt_idx_short=o.get("opt_idx_short"),
            fut_stk_long=o.get("fut_stk_long"),
            fut_stk_short=o.get("fut_stk_short"),
            total_long=o.get("total_long"),
            total_short=o.get("total_short"),
        ))

    if rows:
        _fiidii_cache = (now, rows)
    return rows if rows else _fiidii_cache[1]


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
