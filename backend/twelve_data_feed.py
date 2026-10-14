# backend/twelve_data_feed.py
import asyncio
import json
import logging
import os

import websockets

log = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

_latest: dict[str, float] = {}   # internal key → latest price
_connected: bool = False

# ── Symbol map ────────────────────────────────────────────────────────────────
# Maps Twelve Data symbol → internal key used by data_engine / movers

SYMBOL_MAP: dict[str, str] = {
    # Forex / commodities (original)
    "XAU/USD": "gold",
    "USD/INR": "usdinr",
    # US indices
    "SPX":     "^GSPC",
    "NDX":     "^IXIC",
    "DJI":     "^DJI",
    # US index futures
    "ES1!":    "ES=F",
    "NQ1!":    "NQ=F",
    "YM1!":    "YM=F",
    # European
    "DAX":     "^GDAXI",
    "FTSE":    "^FTSE",
    # Asia-Pacific
    "NI225":   "^N225",
    "HSI":     "^HSI",
    # Commodities
    "WTI/USD": "wti_crude",
    "XAG/USD": "silver",
}

SUBSCRIBE_SYMBOLS: list[str] = list(SYMBOL_MAP.keys())

_WS_URL = "wss://ws.twelvedata.com/v1/quotes/price"

# ── Public getter ─────────────────────────────────────────────────────────────

def get_price(symbol_key: str) -> float | None:
    """Return latest price by internal key (e.g. 'gold', 'usdinr', '^GSPC'), or None."""
    return _latest.get(symbol_key)


def get_live_index_prices() -> dict[str, float]:
    """Return {yfinance_symbol: price} for all live index prices (^GSPC, ^IXIC, etc.)."""
    index_keys = {v for v in SYMBOL_MAP.values() if v.startswith('^') or v.endswith('=F')}
    return {k: v for k, v in _latest.items() if k in index_keys}


# ── Feed coroutine ────────────────────────────────────────────────────────────

async def start_twelve_data_feed() -> None:
    global _connected

    api_key = os.getenv("TWELVE_DATA_KEY", "")
    if not api_key:
        log.warning("[twelve_data] TWELVE_DATA_KEY not set — skipping live feed")
        return

    url = f"{_WS_URL}?apikey={api_key}"
    subscribe_msg = json.dumps({
        "action": "subscribe",
        "params": {"symbols": ",".join(SUBSCRIBE_SYMBOLS)},
    })

    while True:
        try:
            async with websockets.connect(url) as ws:
                await ws.send(subscribe_msg)

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    event = msg.get("event")

                    if event == "subscribe-status":
                        success = msg.get("success", [])
                        fails   = msg.get("fails", [])
                        log.info("[twelve_data] subscribed: %s  failed: %s", success, fails)
                        _connected = True

                    elif event == "price":
                        symbol = msg.get("symbol", "")
                        if symbol in SYMBOL_MAP:
                            price = msg.get("price")
                            if price is not None:
                                _latest[SYMBOL_MAP[symbol]] = float(price)

                    elif event == "heartbeat":
                        pass   # ignore

        except Exception as exc:
            log.warning("[twelve_data] connection error: %s", exc)
        finally:
            _connected = False

        log.info("[twelve_data] reconnecting in 10 s …")
        await asyncio.sleep(10)
