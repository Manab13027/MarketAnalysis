# backend/dhan_feed.py
import asyncio
import json
import logging
import os
import struct

import websockets

from backend.models import IndexQuote

log = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

_latest: dict[str, dict] = {}  # security_id str → {"ltp": float, "prev_close": float, "high": float, "low": float}
_connected: bool = False

# ── Index map ─────────────────────────────────────────────────────────────────

DHAN_INDICES = {
    "13": {"name": "NIFTY 50",   "symbol": "^NSEI"},
    "25": {"name": "Bank NIFTY", "symbol": "^NSEBANK"},
}

_SUBSCRIBE_MSG = {
    "RequestCode": 17,
    "InstrumentCount": 2,
    "InstrumentList": [
        {"ExchangeSegment": "IDX_I", "SecurityId": "13"},
        {"ExchangeSegment": "IDX_I", "SecurityId": "25"},
    ],
}

# ── Packet parser ─────────────────────────────────────────────────────────────

def _parse_packet(data: bytes) -> dict | None:
    if not data:
        return None
    first_byte = data[0]

    if first_byte == 2:
        # Ticker: BHBIfI  (16 bytes)
        if len(data) < 16:
            return None
        fields = struct.unpack('<BHBIfI', data[0:16])
        return {"security_id": fields[3], "ltp": fields[4]}

    if first_byte == 4:
        # Quote: BHBIfHIfIIIffff  (50 bytes)
        if len(data) < 50:
            return None
        fields = struct.unpack('<BHBIfHIfIIIffff', data[0:50])
        return {
            "security_id": fields[3],
            "ltp":         fields[4],
            "prev_close":  fields[12],
            "high":        fields[13],
            "low":         fields[14],
        }

    if first_byte == 6:
        # PrevClose: BHBIfI  (16 bytes)
        if len(data) < 16:
            return None
        fields = struct.unpack('<BHBIfI', data[0:16])
        return {"security_id": fields[3], "prev_close": fields[4]}

    if first_byte == 50:
        raise ConnectionError("Dhan server disconnected")

    return None


# ── State updater ─────────────────────────────────────────────────────────────

def _update_latest(parsed: dict) -> None:
    sid = str(parsed["security_id"])
    entry = _latest.setdefault(sid, {})
    for key in ("ltp", "prev_close", "high", "low"):
        if key in parsed:
            entry[key] = parsed[key]


# ── Public getter ─────────────────────────────────────────────────────────────

def get_latest_indian_quotes() -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for sid, meta in DHAN_INDICES.items():
        entry = _latest.get(sid)
        if not entry or "ltp" not in entry:
            continue
        ltp = entry["ltp"]
        prev = entry.get("prev_close", ltp)
        if prev == 0:
            prev = ltp
        change = round(ltp - prev, 3)
        change_pct = round(change / prev * 100, 3) if prev else 0.0
        quotes.append(IndexQuote(
            symbol=meta["symbol"],
            name=meta["name"],
            price=round(ltp, 2),
            change=change,
            change_pct=change_pct,
        ))
    return quotes


# ── Feed coroutine ────────────────────────────────────────────────────────────

async def start_dhan_feed() -> None:
    global _connected

    client_id = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
    if not client_id or not access_token:
        log.warning("[dhan_feed] DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN not set — skipping live feed")
        return

    url = (
        f"wss://api-feed.dhan.co"
        f"?version=2&token={access_token}&clientId={client_id}&authType=2"
    )

    while True:
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(_SUBSCRIBE_MSG))
                _connected = True
                log.info("[dhan_feed] subscribed to NIFTY 50 + Bank NIFTY")

                async for raw in ws:
                    if isinstance(raw, bytes):
                        parsed = _parse_packet(raw)
                        if parsed:
                            _update_latest(parsed)
                    # text frames (heartbeat etc.) are silently ignored

        except ConnectionError as exc:
            log.warning("[dhan_feed] %s", exc)
        except Exception as exc:
            log.warning("[dhan_feed] connection error: %s", exc)
        finally:
            _connected = False

        log.info("[dhan_feed] reconnecting in 5 s …")
        await asyncio.sleep(5)
