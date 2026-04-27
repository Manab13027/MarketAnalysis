# backend/data_engine.py
import asyncio, os
from datetime import datetime, timezone
from typing import Any
import yfinance as yf

from backend.models import IndexQuote, MarketMovers, WSMessage, MarketStatus
from backend.holiday_calendar import current_market_status

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
    "usdinr":        "USDINR=X",
    "wti_crude":     "CL=F",
    "brent_crude":   "BZ=F",
    "gold":          "GC=F",
    "vix":           "^VIX",
    "us10y":         "^TNX",
    "msci":          "EFA",
    "sp500":         "^GSPC",
    "sp500_futures": "ES=F",
}

POLL_INTERVAL = 10  # seconds


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

    return MarketMovers(
        usdinr=_price("usdinr"),
        wti_crude=_price("wti_crude"),
        brent_crude=_price("brent_crude"),
        gold=_price("gold"),
        vix=_price("vix"),
        us10y=_price("us10y"),
        msci=_price("msci"),
        sp500=_price("sp500"),
        sp500_futures=_price("sp500_futures") or None,
    )




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

            if status_str in ("open", "pre_open"):
                from backend.dhan_feed import get_latest_indian_quotes, _connected as dhan_connected
                global_quotes = fetch_yfinance_quotes(GLOBAL_INDICES)
                if dhan_connected:
                    dhan_quotes = get_latest_indian_quotes()
                else:
                    dhan_quotes = []
                if dhan_quotes:
                    dhan_syms    = {q.symbol for q in dhan_quotes}
                    indian_yf    = [q for q in fetch_yfinance_quotes(INDIAN_INDICES) if q.symbol not in dhan_syms]
                    indian_quotes = dhan_quotes + indian_yf
                else:
                    indian_quotes = fetch_yfinance_quotes(INDIAN_INDICES)
                indices = indian_quotes + global_quotes
            else:
                indices = fetch_yfinance_quotes(SPOT_INDICES) + fetch_futures_quotes()

            movers = fetch_market_movers()

            # ML prediction (sync, in thread pool)
            ml_engine = app_state.get("ml_engine")
            ml_pred = None
            if ml_engine and movers.usdinr > 0:
                loop = asyncio.get_running_loop()
                ml_pred = await loop.run_in_executor(
                    None,
                    ml_engine.predict,
                    movers.usdinr,
                    movers.wti_crude,
                    movers.msci,
                    movers.vix,
                    movers.sp500,
                )

            payload = WSMessage(
                type="market_update",
                timestamp=datetime.now(timezone.utc),
                market_status=market_status,
                indices=indices,
                ml_prediction=ml_pred,
                llm_analysis=app_state.get("latest_llm_analysis"),
                news=app_state.get("latest_news", []),
                market_movers=movers,
            ).model_dump()

            app_state["latest_payload"] = payload
            await manager.broadcast(payload)

        except Exception as exc:
            print(f"[data_engine] error: {exc}")

        await asyncio.sleep(POLL_INTERVAL)
