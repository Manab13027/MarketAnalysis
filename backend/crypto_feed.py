# backend/crypto_feed.py
"""
CoinGecko polling for crypto prices — no API key required.
Polls every 60 s (free tier respects ~30 req/min).
24/7 data source; works on market holidays.
"""
import asyncio
import logging
import time
from typing import Any

log = logging.getLogger(__name__)

_COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum,solana"
    "&vs_currencies=usd"
    "&include_24hr_change=true"
    "&include_market_cap=true"
)

POLL_INTERVAL = 60  # seconds

# Shared state ─────────────────────────────────────────────────────────────────
_latest: dict[str, dict] = {}   # e.g. {"bitcoin": {"usd": 67000, "usd_24h_change": 1.2}}
_last_fetch: float = 0.0
_available: bool = False         # True once first successful fetch


def get_crypto_prices() -> dict[str, dict]:
    """Return cached crypto data — never blocks."""
    return _latest.copy()


def is_available() -> bool:
    return _available


async def start_crypto_feed() -> None:
    """Background task: poll CoinGecko every 60 s."""
    global _latest, _last_fetch, _available

    import aiohttp

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(_COINGECKO_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data: dict[str, Any] = await resp.json()
                        _latest = data
                        _last_fetch = time.monotonic()
                        _available = True
                        log.debug("[crypto_feed] updated: %s", list(data.keys()))
                    elif resp.status == 429:
                        log.warning("[crypto_feed] rate-limited (429) — backing off 120 s")
                        await asyncio.sleep(120)
                        continue
                    else:
                        log.warning("[crypto_feed] HTTP %s", resp.status)
        except Exception as exc:
            log.warning("[crypto_feed] error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)
