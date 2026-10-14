# backend/dhan_feed.py
import asyncio
import csv
import datetime as dt
import io
import json
import logging
import os
import struct
import time

import httpx
import websockets

from backend.models import FuturesContract, IndexQuote

log = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

_latest: dict[str, dict] = {}        # security_id → {ltp, prev_close, high, low}
_connected: bool = False

# ── Index map (always subscribed) ────────────────────────────────────────────

DHAN_INDICES = {
    "13": {"name": "NIFTY 50",   "symbol": "^NSEI"},
    "25": {"name": "Bank NIFTY", "symbol": "^NSEBANK"},
}

# ── Futures state (populated from scrip master) ───────────────────────────────

# security_id → {symbol, expiry (date), label}
_futures_map: dict[str, dict] = {}
_scrip_last_fetch: float = 0.0
SCRIP_REFRESH_SEC = 6 * 3600   # refresh every 6 hours (covers expiry roll-over)


def _fetch_nifty_futures_ids() -> dict[str, dict]:
    """
    Download Dhan scrip master and return the 3 nearest NIFTY 50 futures contracts
    whose expiry >= today.  Returns dict: security_id → {label, expiry_str, expiry}
    """
    today = dt.date.today()
    try:
        r = httpx.get(
            "https://images.dhan.co/api-data/api-scrip-master.csv",
            timeout=60,
            follow_redirects=True,
        )
        r.raise_for_status()
    except Exception as exc:
        log.warning("[dhan_feed] scrip master download failed: %s", exc)
        return {}

    reader = csv.DictReader(io.StringIO(r.text))
    futures: list[dict] = []
    for row in reader:
        sym  = row.get("SEM_TRADING_SYMBOL", "")
        inst = row.get("SEM_INSTRUMENT_NAME", "")
        exch = row.get("SEM_EXM_EXCH_ID", "")
        if not (sym.startswith("NIFTY-") and inst == "FUTIDX" and exch == "NSE"):
            continue
        expiry_raw = row.get("SEM_EXPIRY_DATE", "")
        try:
            expiry_dt = dt.datetime.strptime(expiry_raw, "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            continue
        if expiry_dt < today:
            continue
        sid = row.get("SEM_SMST_SECURITY_ID", "")
        mon_str = expiry_dt.strftime("%b %Y")
        futures.append({
            "security_id": sid,
            "label":       f"NIFTY {mon_str}",
            "expiry":      expiry_dt,
            "expiry_str":  expiry_dt.strftime("%d-%b-%Y"),
        })

    futures.sort(key=lambda x: x["expiry"])
    result = {f["security_id"]: f for f in futures[:3]}
    log.info("[dhan_feed] loaded %d NIFTY futures from scrip master: %s",
             len(result), [f["label"] for f in result.values()])
    return result


# ── Packet parser ─────────────────────────────────────────────────────────────

def _parse_packet(data: bytes) -> dict | None:
    if not data:
        return None
    first_byte = data[0]

    if first_byte == 2:
        # Ticker: BHBIfI  (16 bytes)
        if len(data) < 16:
            return None
        fields = struct.unpack("<BHBIfI", data[0:16])
        return {"security_id": fields[3], "ltp": fields[4]}

    if first_byte == 4:
        # Quote: BHBIfHIfIIIffff  (50 bytes)
        if len(data) < 50:
            return None
        fields = struct.unpack("<BHBIfHIfIIIffff", data[0:50])
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
        fields = struct.unpack("<BHBIfI", data[0:16])
        return {"security_id": fields[3], "prev_close": fields[4]}

    if first_byte == 50:
        if len(data) >= 10:
            fields = struct.unpack("<BHBIH", data[0:10])
            code = fields[4]
            if code == 806:
                raise PermissionError("Dhan Data API subscription required (error 806)")
            if code == 807:
                raise PermissionError("Dhan access token expired (error 807)")
        raise ConnectionError("Dhan server disconnected")

    return None


# ── State updater ─────────────────────────────────────────────────────────────

def _update_latest(parsed: dict) -> None:
    sid = str(parsed["security_id"])
    entry = _latest.setdefault(sid, {})
    for key in ("ltp", "prev_close", "high", "low"):
        if key in parsed:
            entry[key] = parsed[key]


# ── Public getters ────────────────────────────────────────────────────────────

def get_latest_indian_quotes() -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for sid, meta in DHAN_INDICES.items():
        entry = _latest.get(sid)
        if not entry or "ltp" not in entry:
            continue
        ltp  = entry["ltp"]
        prev = entry.get("prev_close", ltp) or ltp
        change     = round(ltp - prev, 3)
        change_pct = round(change / prev * 100, 3) if prev else 0.0
        quotes.append(IndexQuote(
            symbol=meta["symbol"],
            name=meta["name"],
            price=round(ltp, 2),
            change=change,
            change_pct=change_pct,
        ))
    return quotes


def get_latest_nifty_futures() -> list[FuturesContract]:
    """Return live NIFTY futures contracts from Dhan WebSocket ticks."""
    contracts: list[FuturesContract] = []
    for sid, meta in _futures_map.items():
        entry = _latest.get(sid)
        if not entry or "ltp" not in entry:
            continue
        ltp  = entry["ltp"]
        prev = entry.get("prev_close", ltp) or ltp
        change     = round(ltp - prev, 2)
        change_pct = round(change / prev * 100, 3) if prev else 0.0
        contracts.append(FuturesContract(
            label=meta["label"],
            expiry=meta["expiry_str"],
            price=round(ltp, 2),
            change=change,
            change_pct=change_pct,
            oi=None,
            is_gift=False,
            is_prev_close=False,
        ))
    contracts.sort(key=lambda c: c.expiry)
    return contracts


# ── Build subscribe message ───────────────────────────────────────────────────

def _build_subscribe_msg() -> dict:
    instruments = [
        {"ExchangeSegment": "IDX_I", "SecurityId": "13"},   # NIFTY 50
        {"ExchangeSegment": "IDX_I", "SecurityId": "25"},   # Bank NIFTY
    ]
    for sid in _futures_map:
        instruments.append({"ExchangeSegment": "NSE_FNO", "SecurityId": sid})

    return {
        "RequestCode": 17,
        "InstrumentCount": len(instruments),
        "InstrumentList": instruments,
    }


# ── Feed coroutine ────────────────────────────────────────────────────────────

async def start_dhan_feed() -> None:
    global _connected, _futures_map, _scrip_last_fetch

    client_id    = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
    if not client_id or not access_token:
        log.warning("[dhan_feed] DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN not set — skipping")
        return

    # Fetch scrip master to get NIFTY futures IDs
    loop = asyncio.get_running_loop()
    _futures_map = await loop.run_in_executor(None, _fetch_nifty_futures_ids)
    _scrip_last_fetch = time.monotonic()

    url = (
        f"wss://api-feed.dhan.co"
        f"?version=2&token={access_token}&clientId={client_id}&authType=2"
    )

    while True:
        # Refresh scrip master if overdue (handles monthly expiry roll-over)
        now = time.monotonic()
        if now - _scrip_last_fetch > SCRIP_REFRESH_SEC:
            _futures_map = await loop.run_in_executor(None, _fetch_nifty_futures_ids)
            _scrip_last_fetch = now

        subscribe_msg = _build_subscribe_msg()

        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(subscribe_msg))
                _connected = True
                n_fut = len(_futures_map)
                log.info("[dhan_feed] subscribed: NIFTY 50 + Bank NIFTY + %d NIFTY futures", n_fut)

                async for raw in ws:
                    if isinstance(raw, bytes):
                        parsed = _parse_packet(raw)
                        if parsed:
                            _update_latest(parsed)

        except PermissionError as exc:
            log.warning("[dhan_feed] %s — live feed disabled", exc)
            _connected = False
            return   # subscription issue — no retry
        except ConnectionError as exc:
            log.warning("[dhan_feed] %s", exc)
        except Exception as exc:
            log.warning("[dhan_feed] connection error: %s", exc)
        finally:
            _connected = False

        log.info("[dhan_feed] reconnecting in 30 s …")
        await asyncio.sleep(30)
