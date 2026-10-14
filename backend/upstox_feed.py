# backend/upstox_feed.py
"""
Upstox live market feed for NIFTY + GIFT NIFTY futures and indices.

Auth flow (once per day):
  1. User visits http://localhost:8000/upstox/auth  → redirected to Upstox login
  2. After login Upstox calls back http://localhost:8000/upstox/callback?code=...
  3. Backend exchanges code for access_token → stores in memory + .env
  4. start_upstox_feed() reconnects automatically

Instrument keys fetched dynamically from Upstox instrument master (daily).
"""
from __future__ import annotations

import asyncio
import csv
import datetime as dt
import gzip
import io
import json
import logging
import os
import ssl
import threading
import time
from pathlib import Path

import httpx
import upstox_client
import websocket
from google.protobuf import json_format
from upstox_client.feeder.proto import MarketDataFeedV3_pb2

from backend.models import FuturesContract, IndexQuote

log = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

_access_token:   str  = ""
_connected:      bool = False
_latest:         dict[str, dict] = {}   # instrument_key → {ltp, close, ...}

# ── Instrument key constants ──────────────────────────────────────────────────

# Upstox index keys (these don't change)
UPSTOX_INDICES = {
    "NSE_INDEX|Nifty 50":   {"symbol": "^NSEI",    "name": "NIFTY 50"},
    "NSE_INDEX|Nifty Bank": {"symbol": "^NSEBANK",  "name": "Bank NIFTY"},
}

# Futures map: instrument_key → {label, expiry_str, expiry}
_futures_map:      dict[str, dict] = {}
_scrip_last_fetch: float = 0.0
SCRIP_TTL = 6 * 3600   # 6 hours


# ── Instrument master ─────────────────────────────────────────────────────────

def _fetch_nifty_futures_keys() -> dict[str, dict]:
    """Return 3 nearest NIFTY 50 index futures from Upstox instrument master."""
    today = dt.date.today()
    try:
        r = httpx.get(
            "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz",
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
    except Exception as exc:
        log.warning("[upstox_feed] instrument master download failed: %s", exc)
        return {}

    futures: list[dict] = []
    with gzip.open(io.BytesIO(r.content), "rt") as f:
        for row in csv.DictReader(f):
            exch = row.get("exchange", "")
            inst = row.get("instrument_type", "")
            sym  = row.get("tradingsymbol", "")
            key  = row.get("instrument_key", "")
            # Pure NIFTY 50 futures only (skip BANKNIFTY, NIFTYNXT50, etc.)
            if not (exch == "NSE_FO" and inst == "FUTIDX" and
                    sym.startswith("NIFTY") and
                    not any(x in sym for x in ("BANK", "NXT", "MID", "FIN", "CPSE", "NEXT"))):
                continue
            exp_str = row.get("expiry", "")
            try:
                exp_dt = dt.date.fromisoformat(exp_str)
            except Exception:
                continue
            if exp_dt < today:
                continue
            mon_str = exp_dt.strftime("%b %Y")
            futures.append({
                "instrument_key": key,
                "label":          f"NIFTY {mon_str}",
                "expiry":         exp_dt,
                "expiry_str":     exp_dt.strftime("%d-%b-%Y"),
            })

    futures.sort(key=lambda x: x["expiry"])
    result = {f["instrument_key"]: f for f in futures[:3]}
    log.info("[upstox_feed] loaded %d NIFTY futures keys: %s",
             len(result), [f["label"] for f in result.values()])
    return result


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def get_auth_url() -> str:
    api_key      = os.getenv("UPSTOX_API_KEY", "")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://127.0.0.1:8000/upstox/callback")
    return (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"
    )


def exchange_code_for_token(code: str) -> str:
    """Exchange OAuth code for access_token. Returns token string."""
    api_key      = os.getenv("UPSTOX_API_KEY", "")
    api_secret   = os.getenv("UPSTOX_API_SECRET", "")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://127.0.0.1:8000/upstox/callback")
    log.info("[upstox] token exchange — client_id=%s redirect_uri=%s", api_key, redirect_uri)
    r = httpx.post(
        "https://api.upstox.com/v2/login/authorization/token",
        data={
            "code":          code,
            "client_id":     api_key,
            "client_secret": api_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if not r.is_success:
        log.error("[upstox] token exchange failed %s: %s", r.status_code, r.text)
        r.raise_for_status()
    token = r.json().get("access_token", "")
    if token:
        _save_token_to_env(token)
    return token


def exchange_refresh_token(refresh_token: str) -> str:
    """Exchange a refresh token for a new access token and persist it."""
    api_key      = os.getenv("UPSTOX_API_KEY", "")
    api_secret   = os.getenv("UPSTOX_API_SECRET", "")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://127.0.0.1:8000/upstox/callback")
    try:
        r = httpx.post(
            "https://api.upstox.com/v2/login/authorization/token",
            data={
                "refresh_token": refresh_token,
                "client_id":     api_key,
                "client_secret": api_secret,
                "redirect_uri":  redirect_uri,
                "grant_type":    "refresh_token",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        token = r.json().get("access_token", "")
        if token:
            _save_token_to_env(token)
        return token
    except Exception as exc:
        log.warning("[upstox_feed] refresh token exchange failed: %s", exc)
        return ""


def _load_credentials_and_refresh() -> bool:
    """Load credentials file and try to refresh access token.

    Looks for backend/.upstox_credentials.json or ~/.upstox_credentials.json.
    Expects JSON with a `refresh_token` field. Returns True if token loaded.
    """
    candidates = [
        Path(__file__).parent / ".upstox_credentials.json",
        Path.home() / ".upstox_credentials.json",
    ]
    for p in candidates:
        try:
            if not p.exists():
                continue
            data = json.loads(p.read_text())
            refresh = data.get("refresh_token") or data.get("refreshToken")
            if refresh:
                new_token = exchange_refresh_token(refresh)
                if new_token:
                    set_access_token(new_token)
                    log.info("[upstox_feed] loaded access token via refresh token from %s", p)
                    return True
        except Exception as exc:
            log.warning("[upstox_feed] failed reading credentials %s: %s", p, exc)
    return False


def _save_token_to_env(token: str) -> None:
    """Persist the access token back to .env so it survives restarts."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    lines = env_path.read_text().splitlines()
    replaced = False
    new_lines = []
    for line in lines:
        if line.startswith("UPSTOX_ACCESS_TOKEN="):
            new_lines.append(f"UPSTOX_ACCESS_TOKEN={token}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"UPSTOX_ACCESS_TOKEN={token}")
    env_path.write_text("\n".join(new_lines) + "\n")
    log.info("[upstox_feed] access token saved to .env")


def set_access_token(token: str) -> None:
    global _access_token
    _access_token = token
    os.environ["UPSTOX_ACCESS_TOKEN"] = token


# ── Public getters ────────────────────────────────────────────────────────────

def get_latest_indian_quotes() -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for key, meta in UPSTOX_INDICES.items():
        entry = _latest.get(key)
        if not entry or "ltp" not in entry:
            continue
        ltp  = entry["ltp"]
        prev = entry.get("close", ltp) or ltp
        change     = round(ltp - prev, 2)
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
    contracts: list[FuturesContract] = []
    for key, meta in _futures_map.items():
        entry = _latest.get(key)
        if not entry or "ltp" not in entry:
            continue
        ltp  = entry["ltp"]
        prev = entry.get("close", ltp) or ltp
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


# ── Feed coroutine ────────────────────────────────────────────────────────────

async def start_upstox_feed() -> None:
    global _connected, _futures_map, _scrip_last_fetch, _access_token

    api_key = os.getenv("UPSTOX_API_KEY", "")
    if not api_key:
        log.warning("[upstox_feed] UPSTOX_API_KEY not set — skipping")
        return

    # Load token from env if not already set
    if not _access_token:
        _access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")

    # Try credentials file with refresh token to auto-login
    if not _access_token:
        if _load_credentials_and_refresh():
            _access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")

    if not _access_token:
        host_auth = os.getenv("UPSTOX_LOCAL_AUTH_HOST", "http://localhost:8001")
        log.warning("[upstox_feed] No UPSTOX_ACCESS_TOKEN — visit %s/upstox/auth to authenticate", host_auth)
        return

    loop = asyncio.get_running_loop()

    # Fetch instrument keys
    _futures_map = await loop.run_in_executor(None, _fetch_nifty_futures_keys)
    _scrip_last_fetch = time.monotonic()

    all_keys = list(UPSTOX_INDICES.keys()) + list(_futures_map.keys())
    log.info("[upstox_feed] subscribing to %d instruments", len(all_keys))

    while True:
        # Refresh scrip master if needed (handles monthly expiry)
        now = time.monotonic()
        if now - _scrip_last_fetch > SCRIP_TTL:
            _futures_map = await loop.run_in_executor(None, _fetch_nifty_futures_keys)
            _scrip_last_fetch = now
            all_keys = list(UPSTOX_INDICES.keys()) + list(_futures_map.keys())

        close_event = asyncio.Event()
        _loop = asyncio.get_running_loop()
        _ws_ref: list[websocket.WebSocketApp] = []

        try:
            config = upstox_client.Configuration()
            config.access_token = _access_token
            api_client = upstox_client.ApiClient(configuration=config)
            auth_header = api_client.configuration.auth_settings().get("OAUTH2", {}).get("value", "")

            def _subscribe(ws: websocket.WebSocketApp) -> None:
                """Send subscription request — must be sent as binary frame."""
                import uuid as _uuid
                msg = {
                    "guid": str(_uuid.uuid4()),
                    "method": "sub",
                    "data": {
                        "mode": "ltpc",
                        "instrumentKeys": all_keys,
                    },
                }
                ws.send(json.dumps(msg).encode("utf-8"), opcode=websocket.ABNF.OPCODE_BINARY)

            def on_open(ws):
                global _connected
                _connected = True
                _subscribe(ws)
                log.info("[upstox_feed] connected — subscribed to %d instruments", len(all_keys))

            def on_message(ws, raw):
                try:
                    feed_resp = MarketDataFeedV3_pb2.FeedResponse.FromString(raw)
                    data = json_format.MessageToDict(feed_resp)
                    for instr_key, feed_data in data.get("feeds", {}).items():
                        ltpc = feed_data.get("ltpc", {})
                        ltp  = ltpc.get("ltp")
                        cp   = ltpc.get("cp")
                        if ltp is not None:
                            entry = _latest.setdefault(instr_key, {})
                            entry["ltp"] = float(ltp)
                            if cp is not None:
                                entry["close"] = float(cp)
                except Exception as exc:
                    log.debug("[upstox_feed] decode error: %s", exc)

            def on_error(ws, exc):
                log.warning("[upstox_feed] error: %s", exc)

            def on_close(ws, code, msg):
                global _connected
                _connected = False
                log.warning("[upstox_feed] closed (code=%s msg=%s)", code, msg)
                _loop.call_soon_threadsafe(close_event.set)

            ws = websocket.WebSocketApp(
                "wss://api.upstox.com/v3/feed/market-data-feed",
                header={"Authorization": auth_header},
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            _ws_ref.append(ws)

            close_event.clear()
            thread = threading.Thread(
                target=ws.run_forever,
                kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}},
                daemon=True,
            )
            thread.start()

            # Wait up to 10 s for socket to open
            for _ in range(20):
                await asyncio.sleep(0.5)
                if _connected:
                    break
            else:
                log.warning("[upstox_feed] timed out waiting for open")
                ws.close()

            if _connected:
                await close_event.wait()

        except Exception as exc:
            log.warning("[upstox_feed] connection error: %s", exc)
            _connected = False
        finally:
            if _ws_ref:
                _ws_ref[0].close()

        log.info("[upstox_feed] reconnecting in 30 s …")
        await asyncio.sleep(30)
