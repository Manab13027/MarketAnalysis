# backend/data_engine.py
import asyncio, json, os, time
from datetime import datetime, timezone
from typing import Any
import yfinance as yf

from backend.models import FIIDIIEntry, IndexQuote, MarketMovers, WSMessage, MarketStatus, CryptoQuote
from backend.holiday_calendar import current_market_status

# ── FII/DII persistence ───────────────────────────────────────────────────────

_FIIDII_FILE = os.path.join(os.path.dirname(__file__), "data", "fii_dii_last.json")

def _save_fii_dii(data: list) -> None:
    try:
        os.makedirs(os.path.dirname(_FIIDII_FILE), exist_ok=True)
        with open(_FIIDII_FILE, "w") as f:
            json.dump([e.model_dump() for e in data], f)
    except Exception:
        pass

def _load_fii_dii() -> list:
    try:
        if os.path.exists(_FIIDII_FILE):
            with open(_FIIDII_FILE) as f:
                return [FIIDIIEntry(**e) for e in json.load(f)]
    except Exception:
        pass
    return []

# ── Ticker maps ───────────────────────────────────────────────────────────────

INDIAN_INDICES: list[tuple[str, str]] = [
    ("^NSEI",    "NIFTY 50"),
    ("^BSESN",   "SENSEX"),
    ("^NSEBANK", "Bank NIFTY"),
]

GLOBAL_INDICES: list[tuple[str, str]] = [
    ("^GSPC",  "S&P 500"),
    ("^IXIC",  "NASDAQ"),
    ("^GDAXI", "DAX"),
    ("^N225",  "Nikkei 225"),
    ("^HSI",   "Hang Seng"),
]

# Combined for callers that need the full list (backwards compat for tests)
SPOT_INDICES: list[tuple[str, str]] = INDIAN_INDICES + GLOBAL_INDICES

FUTURES_INDICES: list[tuple[str, str]] = [
    ("ES=F",  "S&P 500 Fut"),
    ("YM=F",  "Dow Fut"),
    ("NQ=F",  "NASDAQ Fut"),
    ("NKD=F", "Nikkei Fut"),
]

MOVERS_TICKERS: dict[str, str] = {
    "usdinr":          "USDINR=X",
    "wti_crude":       "CL=F",
    "brent_crude":     "BZ=F",
    "gold":            "GC=F",
    "vix":             "^VIX",
    "us10y":           "^TNX",
    "msci":            "EFA",
    "sp500":           "^GSPC",
    "sp500_futures":   "ES=F",
    "dow_futures":     "YM=F",
    "nasdaq_futures":  "NQ=F",
    "nikkei_futures":  "NKD=F",
}

POLL_INTERVAL    = 10   # seconds
MOVERS_INTERVAL  = 60   # seconds

_movers_cache: dict[str, Any] = {}
_movers_last_fetch: float = 0.0
_nifty_futures_cache: list = []
_fii_dii_cache: list = _load_fii_dii()   # pre-load last known data from disk
_fii_dii_last_fetch: float = 0.0
FII_DII_INTERVAL = 300  # 5 minutes


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct_change(price: float, prev: float) -> float:
    if prev and prev != 0:
        return round((price - prev) / prev * 100, 3)
    return 0.0


def fetch_yfinance_quotes(ticker_pairs: list[tuple[str, str]]) -> list[IndexQuote]:
    symbols = [t[0] for t in ticker_pairs]
    names   = {t[0]: t[1] for t in ticker_pairs}
    try:
        tickers_obj = yf.Tickers(" ".join(symbols))
    except Exception:
        return []
    quotes: list[IndexQuote] = []
    for sym in symbols:
        try:
            t = tickers_obj.tickers[sym]
            price = float(t.fast_info.last_price or 0)
            prev  = float(t.fast_info.previous_close or price)
            quotes.append(IndexQuote(
                symbol=sym,
                name=names[sym],
                price=round(price, 2),
                change=round(price - prev, 2),
                change_pct=_pct_change(price, prev),
                is_futures="=F" in sym,
            ))
        except Exception:
            continue
    return quotes


def fetch_futures_quotes() -> list[IndexQuote]:
    return fetch_yfinance_quotes(FUTURES_INDICES)


def fetch_market_movers() -> MarketMovers:
    syms = list(MOVERS_TICKERS.values())
    try:
        tickers_obj = yf.Tickers(" ".join(syms))
    except Exception:
        return MarketMovers(usdinr=0, wti_crude=0, brent_crude=0, gold=0,
                            vix=0, us10y=0, msci=0, sp500=0)

    def _price(key: str) -> float:
        sym = MOVERS_TICKERS[key]
        try:
            return round(float(tickers_obj.tickers[sym].fast_info.last_price or 0), 4)
        except Exception:
            return 0.0

    movers = MarketMovers(
        usdinr=_price("usdinr"),
        wti_crude=_price("wti_crude"),
        brent_crude=_price("brent_crude"),
        gold=_price("gold"),
        vix=_price("vix"),
        us10y=_price("us10y"),
        msci=_price("msci"),
        sp500=_price("sp500"),
        sp500_futures=_price("sp500_futures")  or None,
        dow_futures=_price("dow_futures")      or None,
        nasdaq_futures=_price("nasdaq_futures") or None,
        nikkei_futures=_price("nikkei_futures") or None,
    )

    # Override with Twelve Data live prices where available
    from backend.twelve_data_feed import get_price as td_get_price, _connected as td_connected
    if td_connected:
        td_gold   = td_get_price("gold")
        td_usdinr = td_get_price("usdinr")
        updates: dict = {}
        if td_gold:
            updates["gold"] = td_gold
        if td_usdinr:
            updates["usdinr"] = td_usdinr
        if updates:
            movers = movers.model_copy(update=updates)

    return movers




# ── Main polling loop ─────────────────────────────────────────────────────────

async def start_data_engine(
    manager: Any,
    app_state: dict[str, Any],
    db_path: str,
) -> None:
    while True:
        try:
            status_str = current_market_status()
            market_status = MarketStatus(
                status=status_str,
                message=(
                    "MARKET CLOSED — Futures Mode" if status_str == "futures_mode"
                    else "MARKET HOLIDAY — Futures Mode" if status_str == "holiday"
                    else None
                ),
            )

            # Always fetch global indices + US futures for the Global Markets panel
            global_quotes  = fetch_yfinance_quotes(GLOBAL_INDICES)
            futures_quotes = fetch_futures_quotes()   # ES=F, YM=F, NQ=F, NKD=F

            if status_str in ("open", "pre_open"):
                from backend.dhan_feed import get_latest_indian_quotes, _connected as dhan_connected
                if dhan_connected:
                    dhan_quotes = get_latest_indian_quotes()
                else:
                    dhan_quotes = []
                if dhan_quotes:
                    dhan_syms     = {q.symbol for q in dhan_quotes}
                    indian_yf     = [q for q in fetch_yfinance_quotes(INDIAN_INDICES) if q.symbol not in dhan_syms]
                    indian_quotes = dhan_quotes + indian_yf
                else:
                    indian_quotes = fetch_yfinance_quotes(INDIAN_INDICES)
                indices = indian_quotes + global_quotes + futures_quotes
            else:
                indian_quotes = fetch_yfinance_quotes(INDIAN_INDICES)
                indices = indian_quotes + global_quotes + futures_quotes

            # ── Override stale yfinance prices with Twelve Data live stream ────
            from backend.twelve_data_feed import get_live_index_prices, _connected as td_connected
            if td_connected:
                live_prices = get_live_index_prices()
                if live_prices:
                    updated = []
                    for q in indices:
                        if q.symbol in live_prices:
                            new_price = live_prices[q.symbol]
                            prev      = q.price - q.change if q.price != 0 else new_price
                            change    = round(new_price - prev, 2)
                            change_pct = round(change / prev * 100, 3) if prev else 0.0
                            updated.append(q.model_copy(update={
                                "price": round(new_price, 2),
                                "change": change,
                                "change_pct": change_pct,
                            }))
                        else:
                            updated.append(q)
                    indices = updated

            movers = fetch_market_movers()

            # ── Add silver from Twelve Data if available ──────────────────────
            from backend.twelve_data_feed import get_price as td_price
            silver_price = td_price("silver")
            if silver_price:
                movers = movers.model_copy(update={"silver": silver_price})

            # ML prediction (sync, in thread pool)
            ml_engine = app_state.get("ml_engine")
            ml_pred = None
            if ml_engine and movers.usdinr > 0:
                # Get live NIFTY price from indices for accurate today_close
                nifty_live = next(
                    (q.price for q in indices if q.symbol == "^NSEI" and q.price > 0),
                    None,
                )
                loop = asyncio.get_running_loop()
                ml_pred = await loop.run_in_executor(
                    None,
                    ml_engine.predict,
                    movers.usdinr,
                    movers.wti_crude,
                    movers.msci,
                    movers.vix,
                    movers.sp500,
                    nifty_live,
                )

            # ── FII / DII (every 5 min) ────────────────────────────────────
            global _fii_dii_cache, _fii_dii_last_fetch
            now_mono = time.monotonic()
            if now_mono - _fii_dii_last_fetch > FII_DII_INTERVAL:
                from backend.market_breadth import fetch_fii_dii
                try:
                    loop = asyncio.get_running_loop()
                    fii_dii = await loop.run_in_executor(None, fetch_fii_dii)
                    if fii_dii:
                        _fii_dii_cache = fii_dii
                        _save_fii_dii(fii_dii)   # persist so restarts show last data
                    _fii_dii_last_fetch = now_mono
                except Exception as e:
                    print(f"[data_engine] fii/dii error: {e}")

            # ── NIFTY futures: Upstox → Dhan → bhav copy fallback ────────────
            global _movers_cache, _movers_last_fetch, _nifty_futures_cache
            from backend.upstox_feed import (
                get_latest_nifty_futures as upstox_futures,
                _connected as upstox_connected,
            )
            from backend.dhan_feed import (
                get_latest_nifty_futures as dhan_futures,
                _connected as dhan_connected,
            )
            if upstox_connected:
                live_fut = upstox_futures()
                if live_fut:
                    _nifty_futures_cache = live_fut
            elif dhan_connected:
                live_fut = dhan_futures()
                if live_fut:
                    _nifty_futures_cache = live_fut

            # ── Index movers + bhav-copy futures fallback (every 60 s) ────────
            if now_mono - _movers_last_fetch > MOVERS_INTERVAL:
                from backend.market_breadth import fetch_index_movers, fetch_nifty_futures
                loop = asyncio.get_running_loop()
                for key in ("nifty50", "banknifty", "midcap", "sensex"):
                    try:
                        result = await loop.run_in_executor(None, fetch_index_movers, key)
                        _movers_cache[key] = result
                    except Exception as e:
                        print(f"[data_engine] movers error {key}: {e}")
                # Only use bhav-copy if neither live feed is active
                if not upstox_connected and not dhan_connected:
                    try:
                        nifty_fut = await loop.run_in_executor(None, fetch_nifty_futures)
                        if nifty_fut:
                            _nifty_futures_cache = nifty_fut
                    except Exception as e:
                        print(f"[data_engine] nifty futures error: {e}")
                _movers_last_fetch = now_mono

            # ── Crypto (CoinGecko, 24/7) ───────────────────────────────────────
            from backend.crypto_feed import get_crypto_prices
            _CRYPTO_META = {
                "bitcoin":  ("BTC", "Bitcoin"),
                "ethereum": ("ETH", "Ethereum"),
                "solana":   ("SOL", "Solana"),
            }
            crypto_raw = get_crypto_prices()
            crypto_quotes: list[CryptoQuote] = []
            for cg_id, (sym, name) in _CRYPTO_META.items():
                d = crypto_raw.get(cg_id)
                if d:
                    crypto_quotes.append(CryptoQuote(
                        symbol=sym,
                        name=name,
                        price_usd=float(d.get("usd", 0)),
                        change_pct_24h=float(d.get("usd_24h_change", 0)),
                        market_cap_usd=float(d.get("usd_market_cap", 0)) or None,
                    ))

            payload = WSMessage(
                type="market_update",
                timestamp=datetime.now(timezone.utc),
                market_status=market_status,
                indices=indices,
                ml_prediction=ml_pred,
                llm_analysis=app_state.get("latest_llm_analysis"),
                news=app_state.get("latest_news", []),
                market_movers=movers,
                index_movers={k: v for k, v in _movers_cache.items() if k in ("nifty50","banknifty","midcap","sensex")} or None,
                nifty_futures=_nifty_futures_cache or None,
                fii_dii=_fii_dii_cache or None,
                crypto=crypto_quotes or None,
            ).model_dump()

            app_state["latest_payload"] = payload
            await manager.broadcast(payload)

        except Exception as exc:
            print(f"[data_engine] error: {exc}")

        await asyncio.sleep(POLL_INTERVAL)
