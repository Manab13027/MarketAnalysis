# backend/main.py
import asyncio, json, os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(override=True)
# Claude Desktop sets ANTHROPIC_API_KEY="" in system env — force values from .env
import pathlib as _pl
from dotenv import dotenv_values as _dv
_env_path = _pl.Path(__file__).parent.parent / ".env"
for _k, _v in _dv(_env_path).items():
    if _v:
        os.environ[_k] = _v

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "market.db")


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active = [c for c in self.active if c is not ws]

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

app_state: dict[str, Any] = {
    "latest_payload": None,
    "ml_engine": None,
    "data_engine_task": None,
    "llm_engine_task": None,
    "news_engine_task": None,
    "dhan_feed_task": None,
    "twelve_data_feed_task": None,
    "latest_llm_analysis": None,
    "latest_news": [],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.db import init_db
    from backend.ml_engine import MLEngine
    from backend.data_engine import start_data_engine
    from backend.llm_engine import start_llm_engine
    from backend.news_engine import start_news_engine

    await init_db(DB_PATH)

    ml = MLEngine(db_path=DB_PATH)
    await asyncio.get_running_loop().run_in_executor(None, ml.train)
    app_state["ml_engine"] = ml

    app_state["data_engine_task"] = asyncio.create_task(
        start_data_engine(manager, app_state, DB_PATH)
    )
    app_state["llm_engine_task"] = asyncio.create_task(
        start_llm_engine(app_state, DB_PATH)
    )
    app_state["news_engine_task"] = asyncio.create_task(
        start_news_engine(app_state, DB_PATH)
    )

    # Dhan disabled — Upstox used instead (no daily token refresh needed)
    # from backend.dhan_feed import start_dhan_feed
    # app_state["dhan_feed_task"] = asyncio.create_task(start_dhan_feed())

    from backend.twelve_data_feed import start_twelve_data_feed
    app_state["twelve_data_feed_task"] = asyncio.create_task(start_twelve_data_feed())

    from backend.upstox_feed import start_upstox_feed
    app_state["upstox_feed_task"] = asyncio.create_task(start_upstox_feed())

    from backend.crypto_feed import start_crypto_feed
    app_state["crypto_feed_task"] = asyncio.create_task(start_crypto_feed())

    yield

    for task_key in ("data_engine_task", "llm_engine_task", "news_engine_task",
                     "dhan_feed_task", "twelve_data_feed_task", "upstox_feed_task",
                     "crypto_feed_task"):
        task = app_state.get(task_key)
        if task:
            task.cancel()


app = FastAPI(title="Market Analysis Dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/ml/retrain")
async def retrain():
    ml = app_state["ml_engine"]
    await asyncio.get_running_loop().run_in_executor(None, ml.train)
    return {"status": "retrained", "cv_mape": ml.cv_mape, "cv_dir_accuracy": ml.cv_dir_accuracy}


@app.post("/api/llm/refresh")
async def llm_refresh():
    task = app_state.get("llm_engine_task")
    if task:
        task.cancel()
    from backend.llm_engine import start_llm_engine
    app_state["llm_engine_task"] = asyncio.create_task(
        start_llm_engine(app_state, DB_PATH)
    )
    return {"status": "refreshing"}



# ── Upstox OAuth endpoints ────────────────────────────────────────────────────

@app.get("/upstox/auth")
async def upstox_auth():
    """Redirect browser to Upstox login. Visit once per day."""
    from fastapi.responses import RedirectResponse
    from backend.upstox_feed import get_auth_url
    return RedirectResponse(get_auth_url())


@app.get("/upstox/callback")
async def upstox_callback(code: str):
    """Upstox redirects here after login. Exchanges code for token, starts feed."""
    from fastapi.responses import HTMLResponse
    from backend.upstox_feed import exchange_code_for_token, set_access_token, start_upstox_feed

    try:
        token = exchange_code_for_token(code)
        set_access_token(token)

        # Restart the upstox feed task with the new token
        old_task = app_state.get("upstox_feed_task")
        if old_task:
            old_task.cancel()
        app_state["upstox_feed_task"] = asyncio.create_task(start_upstox_feed())

        return HTMLResponse("""
            <html><body style="font-family:monospace;background:#0f1117;color:#00ff88;padding:40px">
            <h2>✅ Upstox Connected</h2>
            <p>Live NIFTY futures feed is now active.</p>
            <p>Token saved to .env — valid until midnight IST.</p>
            <script>setTimeout(()=>window.close(), 3000)</script>
            </body></html>
        """)
    except Exception as exc:
        return HTMLResponse(f"""
            <html><body style="font-family:monospace;background:#0f1117;color:#ff4444;padding:40px">
            <h2>❌ Auth failed</h2><pre>{exc}</pre>
            </body></html>
        """, status_code=400)


@app.get("/upstox/status")
async def upstox_status():
    from backend.upstox_feed import _connected, _futures_map
    return {
        "connected": _connected,
        "futures": [v["label"] for v in _futures_map.values()],
        "auth_url": "http://localhost:8000/upstox/auth",
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    if app_state["latest_payload"]:
        await ws.send_text(json.dumps(app_state["latest_payload"], default=str))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
