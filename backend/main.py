# backend/main.py
import asyncio, json, os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

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

    from backend.dhan_feed import start_dhan_feed
    app_state["dhan_feed_task"] = asyncio.create_task(start_dhan_feed())

    yield

    for task_key in ("data_engine_task", "llm_engine_task", "news_engine_task", "dhan_feed_task"):
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
