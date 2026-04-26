# Market Analysis Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time web dashboard that streams live Indian and global market data via WebSocket, runs an ML-based next-day NIFTY 50 prediction, and serves LLM-generated qualitative analysis from a FastAPI backend to a React frontend.

**Architecture:** FastAPI backend with a 10-second polling data engine broadcasts market data, ML predictions, news, and LLM analysis over a WebSocket to a React/Vite frontend. An SQLite database caches all data and prediction history. During market holidays the data engine switches to futures-only mode.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, scikit-learn, yfinance, dhanhq, anthropic SDK, newsapi-python, feedparser, SQLite (aiosqlite), React 18, Vite, TypeScript, Recharts, Tailwind CSS.

---

## File Map

```
MarketAnalysis/
├── backend/
│   ├── main.py               # FastAPI app, WebSocket hub, lifespan startup
│   ├── models.py             # All Pydantic schemas
│   ├── db.py                 # SQLite init + CRUD
│   ├── holiday_calendar.py   # NSE holiday detection + market hours
│   ├── data_engine.py        # 10s polling, yfinance, Dhan, futures mode
│   ├── ml_engine.py          # Ridge + Logistic training + live prediction
│   ├── news_engine.py        # NewsAPI + RSS + sentiment tagging
│   ├── llm_engine.py         # Claude API structured analysis
│   ├── data/                 # model.pkl + market.db (auto-created)
│   └── tests/
│       ├── test_models.py
│       ├── test_holiday_calendar.py
│       ├── test_data_engine.py
│       ├── test_ml_engine.py
│       ├── test_news_engine.py
│       └── test_llm_engine.py
├── frontend/
│   ├── src/
│   │   ├── types.ts
│   │   ├── App.tsx
│   │   ├── hooks/useWebSocket.ts
│   │   └── components/
│   │       ├── MarketStatusBanner.tsx
│   │       ├── TickerBar.tsx
│   │       ├── MLPredictionPanel.tsx
│   │       ├── LLMAnalysisPanel.tsx
│   │       ├── NewsFeed.tsx
│   │       └── MarketMoversStrip.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── .env.example
├── requirements.txt
└── start.sh
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `backend/data/.gitkeep`
- Create: `backend/tests/__init__.py`
- Create: `start.sh`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
websockets==13.0
pydantic==2.8.2
aiosqlite==0.20.0
yfinance==0.2.43
dhanhq==2.0.1
anthropic==0.34.2
newsapi-python==0.2.7
feedparser==6.0.11
scikit-learn==1.5.2
numpy==1.26.4
pandas==2.2.2
joblib==1.4.2
holidays==0.55
httpx==0.27.2
python-dotenv==1.0.1
pytest==8.3.2
pytest-asyncio==0.23.8
```

Run: `pip install -r requirements.txt`
Expected: All packages install without errors.

- [ ] **Step 2: Create .env.example**

```bash
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
NEWS_API_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_anthropic_api_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
```

Copy to `.env` and fill in real keys.

- [ ] **Step 3: Create directory structure and start script**

```bash
mkdir -p backend/data backend/tests
touch backend/data/.gitkeep backend/tests/__init__.py
```

Create `start.sh`:
```bash
#!/bin/bash
set -e
echo "Starting Market Analysis Dashboard..."
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../frontend && npm run dev &
FRONTEND_PID=$!
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
wait $BACKEND_PID $FRONTEND_PID
```

```bash
chmod +x start.sh
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.example backend/data/.gitkeep backend/tests/__init__.py start.sh
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Pydantic Models

**Files:**
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
from backend.models import (
    FactorAdjustment, FactorTodayPred, MLPrediction,
    IndexQuote, MarketMovers, NewsItem, LLMAnalysis,
    MarketStatus, WSMessage
)
from datetime import datetime, timezone

def test_ml_prediction_construction():
    pred = MLPrediction(
        today_close=24173.05,
        ml_preliminary=24002.25,
        adjustments={
            "usdinr": FactorAdjustment(value=-56.31, beta=-1.5539, window="15d"),
            "usoil": FactorAdjustment(value=-38.92, beta=-0.1382, window="15d"),
            "msci": FactorAdjustment(value=-43.79, beta=0.9341, window="1mo"),
            "breadth": FactorAdjustment(value=-10.06, beta=0.0204, window="15d"),
        },
        final_prediction=23853.18,
        expected_move=-319.87,
        expected_move_pct=-1.32,
        direction="DOWN",
        p_up=0.400,
        classifier="AGREE",
        classifier_detail="full move",
        confidence=0.201,
        vix_today=18.59,
        vix_range_low=23840.41,
        vix_range_high=24505.69,
        within_vix_range=True,
        factors_today_pred={
            "usdinr": FactorTodayPred(today=94.5485, pred=94.6902, direction="UP"),
            "usoil": FactorTodayPred(today=95.49, pred=96.61, direction="UP"),
            "msci": FactorTodayPred(today=149.50, pred=149.21, direction="DOWN"),
            "breadth": FactorTodayPred(today=0.880, pred=0.862, direction="DOWN"),
        },
        cv_mape=1.25,
        cv_dir_accuracy=49.5,
    )
    assert pred.final_prediction == 23853.18
    assert pred.direction == "DOWN"

def test_ws_message_serializes():
    msg = WSMessage(
        type="market_update",
        timestamp=datetime.now(timezone.utc),
        market_status=MarketStatus(status="open", message=None),
        indices=[],
        ml_prediction=None,
        llm_analysis=None,
        news=[],
        market_movers=MarketMovers(
            usdinr=94.59, wti_crude=95.49, brent_crude=96.1,
            gold=2340.0, vix=18.59, us10y=4.32, msci=149.50, sp500=5218.0,
            sp500_futures=None,
        )
    )
    data = msg.model_dump()
    assert data["type"] == "market_update"
```

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.models'`

- [ ] **Step 2: Create models.py**

```python
# backend/models.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class FactorAdjustment(BaseModel):
    value: float        # adjustment in index points
    beta: float
    window: str         # "15d" or "1mo"


class FactorTodayPred(BaseModel):
    today: float
    pred: float
    direction: Literal["UP", "DOWN"]


class MLPrediction(BaseModel):
    today_close: float
    ml_preliminary: float
    adjustments: dict[str, FactorAdjustment]   # keys: usdinr, usoil, msci, breadth
    final_prediction: float
    expected_move: float
    expected_move_pct: float
    direction: Literal["UP", "DOWN"]
    p_up: float
    classifier: Literal["AGREE", "DISAGREE"]
    classifier_detail: str                      # "full move" or "half move"
    confidence: float
    vix_today: float
    vix_range_low: float
    vix_range_high: float
    within_vix_range: bool
    factors_today_pred: dict[str, FactorTodayPred]
    cv_mape: float
    cv_dir_accuracy: float


class IndexQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    is_futures: bool = False


class MarketMovers(BaseModel):
    usdinr: float
    wti_crude: float
    brent_crude: float
    gold: float
    vix: float
    us10y: float
    msci: float
    sp500: float
    sp500_futures: Optional[float] = None


class NewsItem(BaseModel):
    id: str
    title: str
    source: str
    url: str
    published_at: datetime
    sentiment: Literal["positive", "negative", "neutral"]
    region: Literal["india", "global"]


class LLMAnalysis(BaseModel):
    bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    summary: str
    key_risks: list[str]
    news_impact: str
    watch_levels: dict[str, float]   # keys: support, resistance
    updated_at: datetime


class MarketStatus(BaseModel):
    status: Literal["open", "closed", "holiday", "futures_mode", "pre_open"]
    message: Optional[str] = None


class WSMessage(BaseModel):
    type: Literal["market_update", "error"]
    timestamp: datetime
    market_status: MarketStatus
    indices: list[IndexQuote]
    ml_prediction: Optional[MLPrediction] = None
    llm_analysis: Optional[LLMAnalysis] = None
    news: list[NewsItem]
    market_movers: MarketMovers
```

- [ ] **Step 3: Run tests from project root**

```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
python -m pytest backend/tests/test_models.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat(models): add all Pydantic schemas"
```

---

## Task 3: SQLite Database

**Files:**
- Create: `backend/db.py`
- Create: `backend/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_db.py
import asyncio, pytest, os, tempfile
from datetime import datetime, timezone

@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    return db_path

@pytest.mark.asyncio
async def test_init_and_insert_prediction(tmp_db):
    from backend.db import init_db, save_prediction, get_recent_predictions
    await init_db(tmp_db)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "today_close": 24173.05,
        "final_prediction": 23853.18,
        "direction": "DOWN",
        "p_up": 0.40,
        "cv_mape": 1.25,
        "cv_dir_accuracy": 49.5,
    }
    await save_prediction(tmp_db, row)
    rows = await get_recent_predictions(tmp_db, limit=5)
    assert len(rows) == 1
    assert rows[0]["direction"] == "DOWN"
```

Run: `python -m pytest backend/tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: Create db.py**

```python
# backend/db.py
import aiosqlite
from typing import Any

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    today_close REAL,
    final_prediction REAL,
    direction TEXT,
    p_up REAL,
    cv_mape REAL,
    cv_dir_accuracy REAL
);
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL,
    change_pct REAL
);
CREATE TABLE IF NOT EXISTS news_items (
    id TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    url TEXT,
    published_at TEXT,
    sentiment TEXT,
    region TEXT
);
CREATE TABLE IF NOT EXISTS llm_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bias TEXT,
    confidence TEXT,
    summary TEXT,
    key_risks TEXT,
    news_impact TEXT,
    support REAL,
    resistance REAL
);
CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trained_at TEXT NOT NULL,
    cv_mape REAL,
    cv_dir_accuracy REAL
);
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


async def save_prediction(db_path: str, row: dict[str, Any]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO predictions
               (timestamp, today_close, final_prediction, direction, p_up, cv_mape, cv_dir_accuracy)
               VALUES (:timestamp, :today_close, :final_prediction, :direction, :p_up, :cv_mape, :cv_dir_accuracy)""",
            row,
        )
        await db.commit()


async def get_recent_predictions(db_path: str, limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_news_item(db_path: str, item: dict[str, Any]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO news_items
               (id, title, source, url, published_at, sentiment, region)
               VALUES (:id, :title, :source, :url, :published_at, :sentiment, :region)""",
            item,
        )
        await db.commit()


async def get_recent_news(db_path: str, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM news_items ORDER BY published_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_llm_analysis(db_path: str, row: dict[str, Any]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO llm_analyses
               (timestamp, bias, confidence, summary, key_risks, news_impact, support, resistance)
               VALUES (:timestamp, :bias, :confidence, :summary, :key_risks, :news_impact, :support, :resistance)""",
            row,
        )
        await db.commit()
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest backend/tests/test_db.py -v
```
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/db.py backend/tests/test_db.py
git commit -m "feat(db): SQLite schema and async CRUD helpers"
```

---

## Task 4: FastAPI App + WebSocket Hub

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Create main.py**

```python
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

# ── WebSocket connection manager ──────────────────────────────────────────────

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

# ── Application state shared across modules ──────────────────────────────────

app_state: dict[str, Any] = {
    "latest_payload": None,
    "ml_engine": None,
    "data_engine_task": None,
    "llm_engine_task": None,
}

# ── Lifespan: startup / shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.db import init_db
    from backend.ml_engine import MLEngine
    from backend.data_engine import start_data_engine
    from backend.llm_engine import start_llm_engine

    await init_db(DB_PATH)

    ml = MLEngine(db_path=DB_PATH)
    await asyncio.get_event_loop().run_in_executor(None, ml.train)
    app_state["ml_engine"] = ml

    app_state["data_engine_task"] = asyncio.create_task(
        start_data_engine(manager, app_state, DB_PATH)
    )
    app_state["llm_engine_task"] = asyncio.create_task(
        start_llm_engine(app_state, DB_PATH)
    )

    yield

    for task_key in ("data_engine_task", "llm_engine_task"):
        task = app_state.get(task_key)
        if task:
            task.cancel()


# ── FastAPI setup ─────────────────────────────────────────────────────────────

app = FastAPI(title="Market Analysis Dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/ml/retrain")
async def retrain():
    ml: "MLEngine" = app_state["ml_engine"]
    await asyncio.get_event_loop().run_in_executor(None, ml.train)
    return {"status": "retrained", "cv_mape": ml.cv_mape, "cv_dir_accuracy": ml.cv_dir_accuracy}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send cached payload immediately on connect
    if app_state["latest_payload"]:
        await ws.send_text(json.dumps(app_state["latest_payload"], default=str))
    try:
        while True:
            await ws.receive_text()   # keep alive, ignore client messages
    except WebSocketDisconnect:
        manager.disconnect(ws)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 2: Smoke test — start backend and hit /api/health**

```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
python -m uvicorn backend.main:app --port 8000
```

In a second terminal:
```bash
curl http://localhost:8000/api/health
```
Expected: `{"status":"ok","timestamp":"..."}` — note: will fail on import until data_engine/ml_engine/llm_engine stubs exist. Proceed to stub them first (Tasks 5-13) then return here.

- [ ] **Step 3: Create stubs so main.py can import**

Create `backend/data_engine.py` (stub):
```python
# backend/data_engine.py
import asyncio
from typing import Any
from backend.main import ConnectionManager

async def start_data_engine(manager: ConnectionManager, app_state: dict, db_path: str):
    while True:
        await asyncio.sleep(10)
```

Create `backend/ml_engine.py` (stub):
```python
# backend/ml_engine.py
class MLEngine:
    cv_mape: float = 0.0
    cv_dir_accuracy: float = 0.0
    def __init__(self, db_path: str): self.db_path = db_path
    def train(self): pass
```

Create `backend/llm_engine.py` (stub):
```python
# backend/llm_engine.py
import asyncio
async def start_llm_engine(app_state: dict, db_path: str):
    while True:
        await asyncio.sleep(300)
```

- [ ] **Step 4: Verify health endpoint works**

```bash
python -m uvicorn backend.main:app --port 8000 &
sleep 2 && curl http://localhost:8000/api/health
```
Expected: `{"status":"ok","timestamp":"..."}`

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/data_engine.py backend/ml_engine.py backend/llm_engine.py
git commit -m "feat(api): FastAPI app with WebSocket hub and stub engines"
```

---

## Task 5: Holiday Calendar

**Files:**
- Create: `backend/holiday_calendar.py`
- Create: `backend/tests/test_holiday_calendar.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_holiday_calendar.py
from datetime import date, time
from backend.holiday_calendar import (
    is_nse_holiday, is_market_open, get_market_status
)

def test_republic_day_is_holiday():
    # 26 Jan is always a public holiday in India
    assert is_nse_holiday(date(2026, 1, 26)) is True

def test_regular_monday_is_not_holiday():
    assert is_nse_holiday(date(2026, 4, 13)) is False  # regular Monday

def test_saturday_market_closed():
    status = get_market_status(date(2026, 4, 25), time(10, 0))  # Saturday
    assert status in ("closed", "futures_mode")

def test_weekday_market_open_hours():
    status = get_market_status(date(2026, 4, 28), time(10, 30))  # Monday 10:30
    assert status == "open"

def test_weekday_pre_market():
    status = get_market_status(date(2026, 4, 28), time(9, 0))
    assert status == "pre_open"
```

Run: `python -m pytest backend/tests/test_holiday_calendar.py -v`
Expected: FAIL

- [ ] **Step 2: Implement holiday_calendar.py**

```python
# backend/holiday_calendar.py
from datetime import date, time, datetime, timezone
from typing import Literal
import holidays

MarketStatusLiteral = Literal["open", "closed", "holiday", "futures_mode", "pre_open"]

# NSE trading hours (IST = UTC+5:30)
NSE_OPEN  = time(9, 15)
NSE_CLOSE = time(15, 30)
PRE_OPEN_START = time(9, 0)

# Hardcoded NSE-specific holidays for 2026 that differ from public holidays.
# Update this list each year from https://www.nseindia.com/
NSE_EXTRA_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 31),   # Id-Ul-Fitr (Ramzan Eid) — approximate
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti / Ram Navami
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 4),   # Diwali Laxmi Pujan — approximate
    date(2026, 12, 25),  # Christmas
}

_in_holidays = holidays.India(years=range(2020, 2030))


def is_nse_holiday(d: date) -> bool:
    """Return True if NSE is closed on this date (public holiday or extra)."""
    if d.weekday() >= 5:   # Saturday=5, Sunday=6
        return True
    if d in _in_holidays or d in NSE_EXTRA_HOLIDAYS_2026:
        return True
    return False


def get_market_status(d: date, t: time) -> MarketStatusLiteral:
    """Return market status given a date and time (IST)."""
    if is_nse_holiday(d):
        return "futures_mode"
    if t < PRE_OPEN_START:
        return "closed"
    if PRE_OPEN_START <= t < NSE_OPEN:
        return "pre_open"
    if NSE_OPEN <= t <= NSE_CLOSE:
        return "open"
    return "futures_mode"   # after hours — use futures


def current_market_status() -> MarketStatusLiteral:
    """Return current market status based on IST now."""
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    return get_market_status(now.date(), now.time())
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest backend/tests/test_holiday_calendar.py -v
```
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/holiday_calendar.py backend/tests/test_holiday_calendar.py
git commit -m "feat(calendar): NSE holiday detection and market hours"
```

---

## Task 6: yfinance Data Fetcher

**Files:**
- Rewrite: `backend/data_engine.py` (replaces stub)
- Create: `backend/tests/test_data_engine.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_data_engine.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from backend.data_engine import fetch_yfinance_quotes, fetch_futures_quotes

def make_mock_ticker(price: float, prev_close: float):
    mock = MagicMock()
    mock.fast_info = MagicMock()
    mock.fast_info.last_price = price
    mock.fast_info.previous_close = prev_close
    return mock

@patch("backend.data_engine.yf.Tickers")
def test_fetch_yfinance_quotes_returns_index_quotes(mock_tickers):
    tickers_obj = MagicMock()
    tickers_obj.tickers = {
        "^GSPC": make_mock_ticker(5218.0, 5200.0),
        "^IXIC": make_mock_ticker(16300.0, 16200.0),
    }
    mock_tickers.return_value = tickers_obj
    quotes = fetch_yfinance_quotes(["^GSPC", "^IXIC"])
    assert len(quotes) == 2
    assert quotes[0].price == 5218.0
    assert quotes[0].change_pct == pytest.approx((5218.0 - 5200.0) / 5200.0 * 100, abs=0.01)
```

Run: `python -m pytest backend/tests/test_data_engine.py -v`
Expected: FAIL

- [ ] **Step 2: Implement data_engine.py**

```python
# backend/data_engine.py
import asyncio, os
from datetime import datetime, timezone
from typing import Any
import yfinance as yf

from backend.models import IndexQuote, MarketMovers, WSMessage, MarketStatus
from backend.holiday_calendar import current_market_status

# ── Ticker maps ───────────────────────────────────────────────────────────────

SPOT_INDICES: list[tuple[str, str]] = [
    ("^NSEI",    "NIFTY 50"),
    ("^BSESN",   "SENSEX"),
    ("^NSEBANK", "Bank NIFTY"),
    ("^GSPC",    "S&P 500"),
    ("^IXIC",    "NASDAQ"),
    ("^GDAXI",   "DAX"),
    ("^N225",    "Nikkei 225"),
    ("^HSI",     "Hang Seng"),
]

FUTURES_INDICES: list[tuple[str, str]] = [
    ("ES=F",  "S&P 500 Fut"),
    ("YM=F",  "Dow Fut"),
    ("NQ=F",  "NASDAQ Fut"),
    ("NKD=F", "Nikkei Fut"),
]

MOVERS_TICKERS: dict[str, str] = {
    "usdinr":     "USDINR=X",
    "wti_crude":  "CL=F",
    "brent_crude":"BZ=F",
    "gold":       "GC=F",
    "vix":        "^VIX",
    "us10y":      "^TNX",
    "msci":       "EFA",
    "sp500":      "^GSPC",
    "sp500_futures": "ES=F",
}

# ── Fetch helpers ─────────────────────────────────────────────────────────────

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
                symbol=sym, name=names[sym],
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
        return MarketMovers(usdinr=0,wti_crude=0,brent_crude=0,gold=0,vix=0,us10y=0,msci=0,sp500=0)

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


# ── Dhan API fetcher (Indian indices live during market hours) ─────────────────

def fetch_dhan_quotes() -> list[IndexQuote]:
    """Fetch NIFTY 50, SENSEX, Bank NIFTY via Dhan API."""
    client_id    = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
    if not client_id or not access_token:
        return []
    try:
        from dhanhq import dhanhq
        dhan = dhanhq(client_id, access_token)
        # Dhan indices security IDs (NSE index segment)
        DHAN_INDICES = [
            ("13", "NIFTY 50",    "^NSEI"),
            ("25", "SENSEX",      "^BSESN"),
            ("21", "Bank NIFTY",  "^NSEBANK"),
        ]
        quotes: list[IndexQuote] = []
        for security_id, name, fallback_sym in DHAN_INDICES:
            try:
                resp = dhan.get_ltp_data(
                    security_id=security_id,
                    exchange_segment=dhan.NSE,
                    instrument_type="INDEX",
                )
                price = float(resp["data"]["last_price"])
                prev  = float(resp["data"]["close_price"])
                quotes.append(IndexQuote(
                    symbol=fallback_sym, name=name,
                    price=round(price, 2),
                    change=round(price - prev, 2),
                    change_pct=_pct_change(price, prev),
                ))
            except Exception:
                continue
        return quotes
    except Exception:
        return []


# ── Main polling loop ─────────────────────────────────────────────────────────

async def start_data_engine(
    manager: Any,           # ConnectionManager
    app_state: dict[str, Any],
    db_path: str,
) -> None:
    from backend.db import save_prediction
    POLL_INTERVAL = 10  # seconds

    while True:
        try:
            status_str = current_market_status()
            market_status = MarketStatus(
                status=status_str,
                message="MARKET CLOSED — Futures Mode" if status_str == "futures_mode" else None,
            )

            # Choose which indices to show
            if status_str in ("open", "pre_open"):
                dhan_quotes = fetch_dhan_quotes()
                yf_quotes   = fetch_yfinance_quotes(SPOT_INDICES)
                # Prefer Dhan prices for Indian indices, fall back to yfinance
                dhan_syms = {q.symbol for q in dhan_quotes}
                indices   = dhan_quotes + [q for q in yf_quotes if q.symbol not in dhan_syms]
            else:
                indices = (
                    fetch_yfinance_quotes(SPOT_INDICES) +
                    fetch_futures_quotes()
                )

            movers = fetch_market_movers()

            # Run ML prediction (sync, in thread pool)
            ml_engine = app_state.get("ml_engine")
            ml_pred = None
            if ml_engine and movers.usdinr > 0:
                loop = asyncio.get_event_loop()
                ml_pred = await loop.run_in_executor(
                    None,
                    ml_engine.predict,
                    movers.usdinr,
                    movers.wti_crude,
                    movers.msci,
                    movers.vix,
                    movers.sp500,
                )

            llm_analysis = app_state.get("latest_llm_analysis")

            payload = WSMessage(
                type="market_update",
                timestamp=datetime.now(timezone.utc),
                market_status=market_status,
                indices=indices,
                ml_prediction=ml_pred,
                llm_analysis=llm_analysis,
                news=app_state.get("latest_news", []),
                market_movers=movers,
            ).model_dump()

            app_state["latest_payload"] = payload
            await manager.broadcast(payload)

        except Exception as exc:
            print(f"[data_engine] error: {exc}")

        await asyncio.sleep(POLL_INTERVAL)
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest backend/tests/test_data_engine.py -v
```
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/data_engine.py backend/tests/test_data_engine.py
git commit -m "feat(data-engine): yfinance + Dhan polling with holiday/futures mode"
```

---

## Task 7: ML Engine

**Files:**
- Rewrite: `backend/ml_engine.py` (replaces stub)
- Create: `backend/tests/test_ml_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_ml_engine.py
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import pandas as pd

def make_fake_history(n=300):
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    np.random.seed(42)
    nifty = 20000 + np.cumsum(np.random.randn(n) * 100)
    usdinr = 83 + np.cumsum(np.random.randn(n) * 0.1)
    usoil  = 80 + np.cumsum(np.random.randn(n) * 0.5)
    msci   = 65 + np.cumsum(np.random.randn(n) * 0.3)
    vix    = 15 + np.abs(np.random.randn(n) * 2)
    sp500  = 4500 + np.cumsum(np.random.randn(n) * 20)
    return pd.DataFrame({
        "nifty": nifty, "usdinr": usdinr, "usoil": usoil,
        "msci": msci, "vix": vix, "sp500": sp500
    }, index=dates)

@patch("backend.ml_engine.MLEngine._fetch_historical_data")
def test_train_produces_metrics(mock_fetch):
    from backend.ml_engine import MLEngine
    mock_fetch.return_value = make_fake_history(300)
    ml = MLEngine(db_path=":memory:")
    ml.train()
    assert 0 < ml.cv_mape < 10        # MAPE under 10%
    assert 0 < ml.cv_dir_accuracy <= 1.0

@patch("backend.ml_engine.MLEngine._fetch_historical_data")
def test_predict_returns_ml_prediction(mock_fetch):
    from backend.ml_engine import MLEngine
    from backend.models import MLPrediction
    mock_fetch.return_value = make_fake_history(300)
    ml = MLEngine(db_path=":memory:")
    ml.train()
    pred = ml.predict(
        usdinr=94.55, usoil=95.49, msci=149.50,
        vix=18.59, sp500=5218.0
    )
    assert isinstance(pred, MLPrediction)
    assert pred.direction in ("UP", "DOWN")
    assert 0.0 <= pred.p_up <= 1.0
    assert pred.cv_mape > 0
```

Run: `python -m pytest backend/tests/test_ml_engine.py -v`
Expected: FAIL

- [ ] **Step 2: Implement ml_engine.py**

```python
# backend/ml_engine.py
import os, math
from datetime import datetime, timezone, date, timedelta
from typing import Optional
import numpy as np
import pandas as pd
import joblib
import yfinance as yf
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from backend.models import MLPrediction, FactorAdjustment, FactorTodayPred

NIFTY50_COMPONENTS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
    "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","ULTRACEMCO.NS",
    "TITAN.NS","BAJFINANCE.NS","NESTLEIND.NS","WIPRO.NS","HCLTECH.NS",
    "POWERGRID.NS","SUNPHARMA.NS","NTPC.NS","TECHM.NS","JSWSTEEL.NS",
    "TATAMOTORS.NS","ONGC.NS","TATASTEEL.NS","M&M.NS","GRASIM.NS",
    "ADANIPORTS.NS","COALINDIA.NS","BAJAJFINSV.NS","DIVISLAB.NS","CIPLA.NS",
    "BPCL.NS","DRREDDY.NS","HEROMOTOCO.NS","EICHERMOT.NS","APOLLOHOSP.NS",
    "BRITANNIA.NS","HINDALCO.NS","INDUSINDBK.NS","TATACONSUM.NS",
    "SBILIFE.NS","HDFCLIFE.NS","BAJAJ-AUTO.NS","UPL.NS","LTIM.NS","BEL.NS",
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "data", "model.pkl")
WINDOW_15D = 15
WINDOW_1MO = 21  # ~1 trading month


class MLEngine:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.ridge: Optional[Ridge] = None
        self.clf: Optional[LogisticRegression] = None
        self.scaler: Optional[StandardScaler] = None
        self.cv_mape: float = 0.0
        self.cv_dir_accuracy: float = 0.0
        self._hist: Optional[pd.DataFrame] = None

    # ── Data ─────────────────────────────────────────────────────────────────

    def _fetch_historical_data(self, years: int = 5) -> pd.DataFrame:
        end   = date.today()
        start = end - timedelta(days=years * 365)
        raw = yf.download(
            "^NSEI USDINR=X CL=F EFA ^VIX ^GSPC",
            start=str(start), end=str(end),
            progress=False, auto_adjust=True,
        )
        close = raw["Close"].copy()
        close.columns = ["msci", "sp500", "vix", "usoil", "usdinr", "nifty"]
        close = close.dropna()
        return close

    def _compute_breadth(self, n_days: int = 5) -> pd.Series:
        """Approximate breadth from NIFTY 50 component advances vs declines."""
        try:
            end   = date.today()
            start = end - timedelta(days=n_days + 10)
            raw = yf.download(
                " ".join(NIFTY50_COMPONENTS[:30]),  # limit to 30 for speed
                start=str(start), end=str(end),
                progress=False, auto_adjust=True,
            )
            closes = raw["Close"]
            daily_chg = closes.pct_change()
            advances = (daily_chg > 0).sum(axis=1)
            declines  = (daily_chg < 0).sum(axis=1)
            breadth   = advances / (advances + declines + 1e-9)
            return breadth
        except Exception:
            return pd.Series(dtype=float)

    # ── Feature engineering ───────────────────────────────────────────────────

    def _build_features(self, hist: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        df = hist.copy()
        df["usdinr_chg"] = df["usdinr"].pct_change()
        df["usoil_chg"]  = df["usoil"].pct_change()
        df["msci_chg"]   = df["msci"].pct_change()
        df["sp500_chg"]  = df["sp500"].pct_change()
        df["nifty_next"] = df["nifty"].shift(-1)   # target
        df = df.dropna()
        features = ["usdinr_chg", "usoil_chg", "msci_chg", "vix", "sp500_chg"]
        X = df[features].values
        y = df["nifty_next"].values
        return X, y

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self) -> None:
        hist = self._fetch_historical_data()
        self._hist = hist
        X, y = self._build_features(hist)

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Ridge regression
        self.ridge = Ridge(alpha=1.0)
        self.ridge.fit(X_scaled, y)

        # Classifier for direction
        y_dir = (y[1:] > y[:-1]).astype(int)   # 1=UP, 0=DOWN
        X_dir = X_scaled[:-1]
        self.clf = LogisticRegression(max_iter=1000)
        self.clf.fit(X_dir, y_dir)

        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        mape_scores = cross_val_score(
            Ridge(alpha=1.0), X_scaled, y, cv=tscv,
            scoring="neg_mean_absolute_percentage_error",
        )
        dir_scores = cross_val_score(
            LogisticRegression(max_iter=1000), X_dir, y_dir, cv=tscv, scoring="accuracy"
        )
        self.cv_mape         = round(float(-mape_scores.mean()) * 100, 2)
        self.cv_dir_accuracy = round(float(dir_scores.mean()), 4)

        # Persist
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({
            "ridge": self.ridge, "clf": self.clf, "scaler": self.scaler,
            "cv_mape": self.cv_mape, "cv_dir_accuracy": self.cv_dir_accuracy,
        }, MODEL_PATH)

    def _load_if_needed(self) -> bool:
        if self.ridge:
            return True
        if os.path.exists(MODEL_PATH):
            bundle = joblib.load(MODEL_PATH)
            self.ridge  = bundle["ridge"]
            self.clf    = bundle["clf"]
            self.scaler = bundle["scaler"]
            self.cv_mape         = bundle["cv_mape"]
            self.cv_dir_accuracy = bundle["cv_dir_accuracy"]
            return True
        return False

    # ── Rolling beta for a factor (OLS slope over window) ────────────────────

    def _rolling_beta(self, factor_series: pd.Series, nifty_series: pd.Series, window: int) -> float:
        if len(factor_series) < window:
            return 0.0
        x = factor_series.iloc[-window:].values
        y = nifty_series.iloc[-window:].values
        if x.std() == 0:
            return 0.0
        return float(np.polyfit(x, y, 1)[0])

    # ── Factor next-day prediction (simple extrapolation) ────────────────────

    def _predict_factor(self, series: pd.Series, window: int = 5) -> float:
        if len(series) < 2:
            return float(series.iloc[-1]) if len(series) else 0.0
        slope = np.polyfit(range(window), series.iloc[-window:].values, 1)[0]
        return round(float(series.iloc[-1] + slope), 4)

    # ── Live prediction ───────────────────────────────────────────────────────

    def predict(
        self, usdinr: float, usoil: float, msci: float,
        vix: float, sp500: float,
    ) -> Optional[MLPrediction]:
        if not self._load_if_needed() or self._hist is None:
            return None

        hist = self._hist
        today_close = float(hist["nifty"].iloc[-1])

        # Build current feature vector
        usdinr_chg = (usdinr - float(hist["usdinr"].iloc[-1])) / float(hist["usdinr"].iloc[-1])
        usoil_chg  = (usoil  - float(hist["usoil"].iloc[-1]))  / float(hist["usoil"].iloc[-1])
        msci_chg   = (msci   - float(hist["msci"].iloc[-1]))   / float(hist["msci"].iloc[-1])
        sp500_chg  = (sp500  - float(hist["sp500"].iloc[-1]))  / float(hist["sp500"].iloc[-1])
        X_live = np.array([[usdinr_chg, usoil_chg, msci_chg, vix, sp500_chg]])
        X_scaled = self.scaler.transform(X_live)

        # Preliminary prediction
        ml_preliminary = round(float(self.ridge.predict(X_scaled)[0]), 2)

        # Rolling betas
        nifty_s = hist["nifty"].pct_change().dropna()
        beta_usdinr = self._rolling_beta(hist["usdinr"].pct_change().dropna(), nifty_s, WINDOW_15D)
        beta_usoil  = self._rolling_beta(hist["usoil"].pct_change().dropna(),  nifty_s, WINDOW_15D)
        beta_msci   = self._rolling_beta(hist["msci"].pct_change().dropna(),   nifty_s, WINDOW_1MO)
        beta_sp500  = self._rolling_beta(hist["sp500"].pct_change().dropna(),  nifty_s, WINDOW_15D)

        # Factor adjustments (beta × % change × today_close for point impact)
        adj_usdinr = round(beta_usdinr * usdinr_chg * today_close, 2)
        adj_usoil  = round(beta_usoil  * usoil_chg  * today_close, 2)
        adj_msci   = round(beta_msci   * msci_chg   * today_close, 2)
        adj_breadth = 0.0  # placeholder until breadth is live

        final = round(ml_preliminary + adj_usdinr + adj_usoil + adj_msci + adj_breadth, 2)
        move  = round(final - today_close, 2)
        move_pct = round(move / today_close * 100, 3)
        direction = "UP" if final > today_close else "DOWN"

        # Classifier
        p_up = round(float(self.clf.predict_proba(X_scaled)[0][1]), 4)
        clf_dir = "UP" if p_up > 0.5 else "DOWN"
        agree   = clf_dir == direction
        confidence = round(abs(p_up - 0.5) * 2, 4)
        if not agree:
            final      = round(today_close + move / 2, 2)
            move       = round(final - today_close, 2)
            move_pct   = round(move / today_close * 100, 3)

        # VIX range
        vix_daily_vol = vix / 100 / math.sqrt(252)
        vix_low  = round(today_close * (1 - vix_daily_vol), 2)
        vix_high = round(today_close * (1 + vix_daily_vol), 2)

        # Factor today/predicted
        usdinr_pred = self._predict_factor(hist["usdinr"])
        usoil_pred  = self._predict_factor(hist["usoil"])
        msci_pred   = self._predict_factor(hist["msci"])

        return MLPrediction(
            today_close=today_close,
            ml_preliminary=ml_preliminary,
            adjustments={
                "usdinr":  FactorAdjustment(value=adj_usdinr,  beta=round(beta_usdinr,4), window="15d"),
                "usoil":   FactorAdjustment(value=adj_usoil,   beta=round(beta_usoil,4),  window="15d"),
                "msci":    FactorAdjustment(value=adj_msci,    beta=round(beta_msci,4),   window="1mo"),
                "breadth": FactorAdjustment(value=adj_breadth, beta=0.0,                  window="15d"),
            },
            final_prediction=final,
            expected_move=move,
            expected_move_pct=move_pct,
            direction=direction,
            p_up=p_up,
            classifier="AGREE" if agree else "DISAGREE",
            classifier_detail="full move" if agree else "half move",
            confidence=confidence,
            vix_today=round(vix, 2),
            vix_range_low=vix_low,
            vix_range_high=vix_high,
            within_vix_range=(vix_low <= final <= vix_high),
            factors_today_pred={
                "usdinr": FactorTodayPred(today=round(usdinr,4), pred=usdinr_pred, direction="UP" if usdinr_pred > usdinr else "DOWN"),
                "usoil":  FactorTodayPred(today=round(usoil,2),  pred=usoil_pred,  direction="UP" if usoil_pred > usoil else "DOWN"),
                "msci":   FactorTodayPred(today=round(msci,2),   pred=msci_pred,   direction="UP" if msci_pred > msci else "DOWN"),
                "breadth":FactorTodayPred(today=0.0, pred=0.0, direction="DOWN"),
            },
            cv_mape=self.cv_mape,
            cv_dir_accuracy=round(self.cv_dir_accuracy * 100, 1),
        )
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest backend/tests/test_ml_engine.py -v
```
Expected: 2 PASS (may take 30–60s while yfinance fetch is mocked)

- [ ] **Step 4: Commit**

```bash
git add backend/ml_engine.py backend/tests/test_ml_engine.py
git commit -m "feat(ml): Ridge + Logistic prediction engine with rolling betas"
```

---

## Task 8: News Engine

**Files:**
- Rewrite: `backend/news_engine.py`
- Create: `backend/tests/test_news_engine.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_news_engine.py
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

def make_mock_article(title: str, source: str, url: str):
    return {
        "title": title,
        "source": {"name": source},
        "url": url,
        "publishedAt": "2026-04-26T08:00:00Z",
    }

@patch("backend.news_engine.NewsApiClient")
def test_fetch_news_returns_news_items(mock_client_cls):
    from backend.news_engine import NewsEngine
    from backend.models import NewsItem
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_everything.return_value = {
        "articles": [
            make_mock_article("RBI holds rates", "Moneycontrol", "https://mc.com/1"),
            make_mock_article("Fed cuts likely in 2026", "Reuters", "https://reuters.com/1"),
        ]
    }
    engine = NewsEngine(api_key="test")
    items = engine.fetch()
    assert len(items) == 2
    assert all(isinstance(i, NewsItem) for i in items)

def test_sentiment_tagging():
    from backend.news_engine import tag_sentiment
    assert tag_sentiment("Sensex surges 500 points rally") == "positive"
    assert tag_sentiment("Market crash panic sell-off") == "negative"
    assert tag_sentiment("RBI governor speech today") == "neutral"
```

Run: `python -m pytest backend/tests/test_news_engine.py -v`
Expected: FAIL

- [ ] **Step 2: Implement news_engine.py**

```python
# backend/news_engine.py
import os, hashlib, asyncio
from datetime import datetime, timezone
from typing import Optional

import feedparser
from newsapi import NewsApiClient

from backend.models import NewsItem

POSITIVE_WORDS = {
    "surge", "rally", "gain", "rise", "jump", "bull", "record",
    "growth", "profit", "beat", "recovery", "up", "high", "strong",
}
NEGATIVE_WORDS = {
    "crash", "fall", "drop", "plunge", "sell", "bear", "loss",
    "decline", "weak", "fear", "panic", "down", "low", "recession",
}

INDIA_KEYWORDS  = ["nifty","sensex","bse","nse","india","rbi","sebi","rupee","inr"]
GLOBAL_KEYWORDS = ["fed","s&p","nasdaq","dow","ecb","china","global","wall street","crude","oil"]

RSS_FEEDS = [
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5ENSEI&region=US&lang=en-US", "Yahoo Finance"),
    ("https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2143429.cms", "Economic Times"),
]


def tag_sentiment(title: str) -> str:
    lower = title.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def tag_region(title: str) -> str:
    lower = title.lower()
    if any(w in lower for w in INDIA_KEYWORDS):
        return "india"
    return "global"


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


class NewsEngine:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
        self._client = NewsApiClient(api_key=self.api_key) if self.api_key else None

    def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        items.extend(self._fetch_newsapi())
        items.extend(self._fetch_rss())
        # Deduplicate by id
        seen: set[str] = set()
        unique: list[NewsItem] = []
        for item in items:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)
        return sorted(unique, key=lambda x: x.published_at, reverse=True)[:30]

    def _fetch_newsapi(self) -> list[NewsItem]:
        if not self._client:
            return []
        try:
            resp = self._client.get_everything(
                q="NIFTY OR sensex OR stock market OR RBI OR Fed OR crude oil",
                language="en",
                sort_by="publishedAt",
                page_size=20,
            )
            items = []
            for a in resp.get("articles", []):
                title = a.get("title") or ""
                url   = a.get("url") or ""
                if not title or not url:
                    continue
                items.append(NewsItem(
                    id=_make_id(url),
                    title=title,
                    source=a.get("source", {}).get("name", ""),
                    url=url,
                    published_at=_parse_dt(a.get("publishedAt", "")),
                    sentiment=tag_sentiment(title),
                    region=tag_region(title),
                ))
            return items
        except Exception:
            return []

    def _fetch_rss(self) -> list[NewsItem]:
        items = []
        for feed_url, source_name in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title") or ""
                    url   = entry.get("link") or ""
                    if not title or not url:
                        continue
                    published_str = entry.get("published", "")
                    items.append(NewsItem(
                        id=_make_id(url),
                        title=title,
                        source=source_name,
                        url=url,
                        published_at=_parse_dt(published_str),
                        sentiment=tag_sentiment(title),
                        region=tag_region(title),
                    ))
            except Exception:
                continue
        return items


async def start_news_engine(app_state: dict, db_path: str) -> None:
    from backend.db import save_news_item
    engine = NewsEngine()
    while True:
        try:
            items = engine.fetch()
            app_state["latest_news"] = items
            for item in items:
                await save_news_item(db_path, {
                    "id": item.id, "title": item.title, "source": item.source,
                    "url": item.url, "published_at": item.published_at.isoformat(),
                    "sentiment": item.sentiment, "region": item.region,
                })
        except Exception as e:
            print(f"[news_engine] error: {e}")
        await asyncio.sleep(120)  # refresh every 2 minutes
```

- [ ] **Step 3: Wire news engine into main.py lifespan**

In `backend/main.py`, add to the lifespan startup (after LLM engine task):
```python
from backend.news_engine import start_news_engine
app_state["news_engine_task"] = asyncio.create_task(
    start_news_engine(app_state, DB_PATH)
)
```
And cancel it in shutdown:
```python
for task_key in ("data_engine_task", "llm_engine_task", "news_engine_task"):
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest backend/tests/test_news_engine.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/news_engine.py backend/tests/test_news_engine.py backend/main.py
git commit -m "feat(news): NewsAPI + RSS fetcher with sentiment tagging"
```

---

## Task 9: LLM Engine

**Files:**
- Rewrite: `backend/llm_engine.py`
- Create: `backend/tests/test_llm_engine.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_llm_engine.py
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

FAKE_LLM_RESPONSE = """{
  "bias": "BEARISH",
  "confidence": "MEDIUM",
  "summary": "Global cues remain weak with crude elevated and FII selling likely to continue.",
  "key_risks": ["Elevated crude oil", "FII outflows", "Weak global sentiment"],
  "news_impact": "Fed hold and weak US data add to bearish bias for Asian markets.",
  "watch_levels": {"support": 23800, "resistance": 24400}
}"""

@patch("backend.llm_engine.anthropic.Anthropic")
def test_llm_engine_returns_analysis(mock_anthropic):
    from backend.llm_engine import LLMEngine
    from backend.models import LLMAnalysis

    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    msg = MagicMock()
    msg.content = [MagicMock(text=FAKE_LLM_RESPONSE)]
    mock_client.messages.create.return_value = msg

    engine = LLMEngine()
    analysis = engine.analyze(
        ml_summary="NIFTY pred 23853 DOWN, P(UP)=0.40",
        news_headlines=["RBI holds rates", "FII sells ₹2400Cr"],
        macro={"usdinr": 94.55, "wti_crude": 95.49, "vix": 18.59, "sp500": 5218.0},
        market_status="open",
    )
    assert isinstance(analysis, LLMAnalysis)
    assert analysis.bias == "BEARISH"
    assert len(analysis.key_risks) == 3
    assert "support" in analysis.watch_levels
```

Run: `python -m pytest backend/tests/test_llm_engine.py -v`
Expected: FAIL

- [ ] **Step 2: Implement llm_engine.py**

```python
# backend/llm_engine.py
import asyncio, json, os
from datetime import datetime, timezone
from typing import Optional

import anthropic

from backend.models import LLMAnalysis

SYSTEM_PROMPT = """You are a professional Indian stock market analyst.
Given real-time market data, an ML model prediction, and recent news headlines,
produce a structured market analysis in JSON.

RESPOND ONLY WITH VALID JSON matching this exact schema:
{
  "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "summary": "<2-3 sentences>",
  "key_risks": ["<risk1>", "<risk2>", "<risk3>"],
  "news_impact": "<1-2 sentences on how today's news shifts the outlook>",
  "watch_levels": {"support": <number>, "resistance": <number>}
}"""


class LLMEngine:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def analyze(
        self,
        ml_summary: str,
        news_headlines: list[str],
        macro: dict,
        market_status: str,
    ) -> Optional[LLMAnalysis]:
        if not self._client:
            return None
        news_block = "\n".join(f"• {h}" for h in news_headlines[:10])
        user_msg = f"""Market Status: {market_status}

ML Prediction:
{ml_summary}

Macro Snapshot:
- USD/INR: {macro.get('usdinr', 'N/A')}
- WTI Crude: ${macro.get('wti_crude', 'N/A')}
- VIX: {macro.get('vix', 'N/A')}
- S&P 500: {macro.get('sp500', 'N/A')}

Recent Headlines:
{news_block}

Produce the JSON analysis now."""

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return LLMAnalysis(
                bias=data["bias"],
                confidence=data["confidence"],
                summary=data["summary"],
                key_risks=data["key_risks"],
                news_impact=data["news_impact"],
                watch_levels=data["watch_levels"],
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            print(f"[llm_engine] error: {e}")
            return None


async def start_llm_engine(app_state: dict, db_path: str) -> None:
    from backend.db import save_llm_analysis
    engine = LLMEngine()
    while True:
        await asyncio.sleep(300)   # every 5 minutes
        try:
            ml_pred = app_state.get("latest_payload", {})
            ml_obj  = ml_pred.get("ml_prediction") if ml_pred else None
            ml_summary = (
                f"NIFTY pred {ml_obj['final_prediction']} {ml_obj['direction']}, "
                f"P(UP)={ml_obj['p_up']}, Conf={ml_obj['confidence']}"
                if ml_obj else "ML prediction not available"
            )
            news  = app_state.get("latest_news", [])
            headlines = [n.title if hasattr(n, "title") else n.get("title","") for n in news[:10]]
            movers = ml_pred.get("market_movers", {}) if ml_pred else {}
            macro  = {
                "usdinr":    movers.get("usdinr", 0),
                "wti_crude": movers.get("wti_crude", 0),
                "vix":       movers.get("vix", 0),
                "sp500":     movers.get("sp500", 0),
            }
            status = ml_pred.get("market_status", {}).get("status","unknown") if ml_pred else "unknown"
            analysis = engine.analyze(ml_summary, headlines, macro, status)
            if analysis:
                app_state["latest_llm_analysis"] = analysis
                await save_llm_analysis(db_path, {
                    "timestamp":   analysis.updated_at.isoformat(),
                    "bias":        analysis.bias,
                    "confidence":  analysis.confidence,
                    "summary":     analysis.summary,
                    "key_risks":   json.dumps(analysis.key_risks),
                    "news_impact": analysis.news_impact,
                    "support":     analysis.watch_levels.get("support", 0),
                    "resistance":  analysis.watch_levels.get("resistance", 0),
                })
        except Exception as e:
            print(f"[llm_engine loop] error: {e}")
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest backend/tests/test_llm_engine.py -v
```
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/llm_engine.py backend/tests/test_llm_engine.py
git commit -m "feat(llm): Claude API structured market analysis engine"
```

---

## Task 10: Frontend Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/types.ts`

- [ ] **Step 1: Scaffold React + Vite project**

```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install recharts lucide-react
```

- [ ] **Step 2: Configure Tailwind**

Replace `frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "Menlo", "monospace"],
      },
      colors: {
        terminal: {
          bg:      "#0f1117",
          panel:   "#1a1f2e",
          border:  "#2d3748",
          green:   "#22c55e",
          red:     "#ef4444",
          amber:   "#f59e0b",
          blue:    "#60a5fa",
          muted:   "#64748b",
          label:   "#94a3b8",
          text:    "#e2e8f0",
        }
      }
    }
  },
  plugins: [],
}
```

- [ ] **Step 3: Update index.html to add JetBrains Mono font**

Replace `frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Market Analysis Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-terminal-bg text-terminal-text font-mono">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Update src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; }
body { background: #0f1117; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }
```

- [ ] **Step 5: Create types.ts**

```typescript
// frontend/src/types.ts

export interface FactorAdjustment {
  value: number;
  beta: number;
  window: string;
}

export interface FactorTodayPred {
  today: number;
  pred: number;
  direction: "UP" | "DOWN";
}

export interface MLPrediction {
  today_close: number;
  ml_preliminary: number;
  adjustments: Record<string, FactorAdjustment>;
  final_prediction: number;
  expected_move: number;
  expected_move_pct: number;
  direction: "UP" | "DOWN";
  p_up: number;
  classifier: "AGREE" | "DISAGREE";
  classifier_detail: string;
  confidence: number;
  vix_today: number;
  vix_range_low: number;
  vix_range_high: number;
  within_vix_range: boolean;
  factors_today_pred: Record<string, FactorTodayPred>;
  cv_mape: number;
  cv_dir_accuracy: number;
}

export interface IndexQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  is_futures: boolean;
}

export interface MarketMovers {
  usdinr: number;
  wti_crude: number;
  brent_crude: number;
  gold: number;
  vix: number;
  us10y: number;
  msci: number;
  sp500: number;
  sp500_futures: number | null;
}

export interface NewsItem {
  id: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: "positive" | "negative" | "neutral";
  region: "india" | "global";
}

export interface LLMAnalysis {
  bias: "BULLISH" | "BEARISH" | "NEUTRAL";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  summary: string;
  key_risks: string[];
  news_impact: string;
  watch_levels: { support: number; resistance: number };
  updated_at: string;
}

export interface MarketStatus {
  status: "open" | "closed" | "holiday" | "futures_mode" | "pre_open";
  message: string | null;
}

export interface WSMessage {
  type: "market_update" | "error";
  timestamp: string;
  market_status: MarketStatus;
  indices: IndexQuote[];
  ml_prediction: MLPrediction | null;
  llm_analysis: LLMAnalysis | null;
  news: NewsItem[];
  market_movers: MarketMovers;
}
```

- [ ] **Step 6: Configure vite proxy**

Replace `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws':  { target: 'ws://localhost:8000', ws: true },
    }
  }
})
```

- [ ] **Step 7: Commit**

```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
git add frontend/
git commit -m "feat(frontend): Vite + React + TypeScript + Tailwind dark terminal setup"
```

---

## Task 11: useWebSocket Hook

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Create useWebSocket.ts**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useState, useEffect, useRef, useCallback } from 'react'
import type { WSMessage } from '../types'

type Status = 'connecting' | 'connected' | 'disconnected'

export function useWebSocket(url: string) {
  const [message, setMessage]   = useState<WSMessage | null>(null)
  const [status,  setStatus]    = useState<Status>('connecting')
  const wsRef    = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen  = () => setStatus('connected')
    ws.onclose = () => {
      setStatus('disconnected')
      reconnectRef.current = setTimeout(connect, 3000)
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (e) => {
      try {
        setMessage(JSON.parse(e.data) as WSMessage)
      } catch { /* ignore malformed */ }
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { message, status }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts
git commit -m "feat(frontend): WebSocket hook with auto-reconnect"
```

---

## Task 12: Frontend Components

**Files:**
- Create: `frontend/src/components/MarketStatusBanner.tsx`
- Create: `frontend/src/components/TickerBar.tsx`
- Create: `frontend/src/components/MLPredictionPanel.tsx`
- Create: `frontend/src/components/LLMAnalysisPanel.tsx`
- Create: `frontend/src/components/NewsFeed.tsx`
- Create: `frontend/src/components/MarketMoversStrip.tsx`

- [ ] **Step 1: MarketStatusBanner.tsx**

```tsx
// frontend/src/components/MarketStatusBanner.tsx
import type { MarketStatus } from '../types'

export function MarketStatusBanner({ status }: { status: MarketStatus }) {
  if (status.status === 'open') return null
  const colors: Record<string, string> = {
    futures_mode: 'bg-amber-900/60 text-amber-300 border-amber-600',
    pre_open:     'bg-blue-900/60 text-blue-300 border-blue-600',
    closed:       'bg-terminal-panel text-terminal-muted border-terminal-border',
    holiday:      'bg-purple-900/60 text-purple-300 border-purple-600',
  }
  const cls = colors[status.status] ?? colors.closed
  return (
    <div className={`w-full text-center text-xs py-1 border-b font-semibold tracking-widest uppercase ${cls}`}>
      {status.message ?? status.status.replace('_', ' ')}
    </div>
  )
}
```

- [ ] **Step 2: TickerBar.tsx**

```tsx
// frontend/src/components/TickerBar.tsx
import type { IndexQuote } from '../types'

function TickerItem({ q }: { q: IndexQuote }) {
  const up = q.change_pct >= 0
  return (
    <span className="inline-flex items-center gap-2 px-4 border-r border-terminal-border whitespace-nowrap">
      <span className="text-terminal-label text-xs">{q.name}{q.is_futures ? ' ◆' : ''}</span>
      <span className={`font-semibold ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {q.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </span>
      <span className={`text-xs ${up ? 'text-terminal-green' : 'text-terminal-red'}`}>
        {up ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
      </span>
    </span>
  )
}

export function TickerBar({ indices }: { indices: IndexQuote[] }) {
  return (
    <div className="w-full bg-terminal-panel border-b border-terminal-border overflow-x-auto scrollbar-hide">
      <div className="flex items-center h-10 min-w-max">
        {indices.map(q => <TickerItem key={q.symbol} q={q} />)}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: MLPredictionPanel.tsx**

```tsx
// frontend/src/components/MLPredictionPanel.tsx
import type { MLPrediction } from '../types'

const fmt = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 })
const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`

export function MLPredictionPanel({ pred }: { pred: MLPrediction | null }) {
  if (!pred) return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 h-full flex items-center justify-center">
      <span className="text-terminal-muted text-sm">Training model...</span>
    </div>
  )
  const up = pred.direction === 'UP'
  const dirColor = up ? 'text-terminal-green' : 'text-terminal-red'
  const FACTOR_LABELS: Record<string, string> = {
    usdinr: 'USDINR', usoil: 'USOIL', msci: 'MSCI', breadth: 'BREADTH'
  }
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-sm h-full overflow-y-auto">
      <div className="text-terminal-label text-xs tracking-widest mb-3 border-b border-terminal-border pb-2">
        NIFTY 50 — NEXT-DAY PREDICTION
      </div>

      <div className="text-terminal-label text-xs mb-1">
        Today close : <span className="text-terminal-text">{fmt(pred.today_close)}</span>
      </div>

      <div className="mt-3 space-y-1 text-xs text-terminal-muted">
        <div>[A] ML preliminary : <span className="text-terminal-text">{fmt(pred.ml_preliminary)}</span></div>
        {Object.entries(pred.adjustments).map(([k, v]) => (
          <div key={k}>
            [{['B','C','D','E'][Object.keys(pred.adjustments).indexOf(k)]}]{' '}
            {FACTOR_LABELS[k]} adj : <span className={v.value >= 0 ? 'text-terminal-green' : 'text-terminal-red'}>{v.value >= 0 ? '+' : ''}{fmt(v.value)}</span>
            <span className="text-terminal-muted ml-2">(β={v.beta} w={v.window})</span>
          </div>
        ))}
      </div>

      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-xs">
        <div className={`text-base font-bold ${dirColor}`}>
          FINAL : {fmt(pred.final_prediction)} {up ? '▲' : '▼'} {pred.direction}
        </div>
        <div>Expected move : <span className={dirColor}>{fmtPct(pred.expected_move_pct)} ({pred.expected_move >= 0 ? '+' : ''}{fmt(pred.expected_move)} pts)</span></div>
        <div>P(UP) : <span className="text-terminal-text">{pred.p_up.toFixed(3)}</span></div>
        <div>Classifier : <span className={pred.classifier === 'AGREE' ? 'text-terminal-green' : 'text-terminal-amber'}>{pred.classifier} — {pred.classifier_detail}</span></div>
        <div>Confidence : <span className="text-terminal-text">{pred.confidence.toFixed(3)}</span></div>
      </div>

      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-xs text-terminal-muted">
        <div>VIX today : <span className="text-terminal-text">{pred.vix_today.toFixed(2)}%</span></div>
        <div>VIX range : <span className="text-terminal-text">{fmt(pred.vix_range_low)} – {fmt(pred.vix_range_high)}</span></div>
        <div>Within VIX range? : <span className={pred.within_vix_range ? 'text-terminal-green' : 'text-terminal-red'}>{pred.within_vix_range ? 'YES' : 'NO'}</span></div>
      </div>

      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-xs text-terminal-muted">
        {Object.entries(pred.factors_today_pred).map(([k, v]) => (
          <div key={k}>
            {FACTOR_LABELS[k]} today/pred :
            <span className="text-terminal-text"> {v.today} / {v.pred}</span>
            <span className={v.direction === 'UP' ? 'text-terminal-green ml-1' : 'text-terminal-red ml-1'}>({v.direction})</span>
          </div>
        ))}
      </div>

      <div className="border-t border-terminal-border mt-3 pt-3 space-y-1 text-xs text-terminal-muted">
        <div>CV MAPE : <span className="text-terminal-text">{pred.cv_mape.toFixed(2)}%</span></div>
        <div>CV Dir Accuracy : <span className="text-terminal-text">{pred.cv_dir_accuracy.toFixed(1)}%</span></div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: LLMAnalysisPanel.tsx**

```tsx
// frontend/src/components/LLMAnalysisPanel.tsx
import type { LLMAnalysis } from '../types'

export function LLMAnalysisPanel({
  analysis, onRefresh
}: {
  analysis: LLMAnalysis | null
  onRefresh: () => void
}) {
  const biasColor = analysis
    ? analysis.bias === 'BULLISH' ? 'text-terminal-green'
    : analysis.bias === 'BEARISH' ? 'text-terminal-red'
    : 'text-terminal-amber'
    : ''

  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-sm h-full overflow-y-auto">
      <div className="text-terminal-label text-xs tracking-widest mb-3 border-b border-terminal-border pb-2">
        LLM ANALYSIS
      </div>
      {!analysis ? (
        <p className="text-terminal-muted text-xs">Waiting for analysis (updates every 5 min)...</p>
      ) : (
        <div className="space-y-3 text-xs">
          <div>
            <span className="text-terminal-label">Bias : </span>
            <span className={`font-bold ${biasColor}`}>{analysis.bias}</span>
            <span className="text-terminal-muted ml-2">({analysis.confidence} confidence)</span>
          </div>
          <p className="text-terminal-text leading-relaxed">{analysis.summary}</p>
          <div>
            <div className="text-terminal-label mb-1">Key Risks :</div>
            {analysis.key_risks.map((r, i) => (
              <div key={i} className="text-terminal-muted">• {r}</div>
            ))}
          </div>
          <div>
            <span className="text-terminal-label">News Impact : </span>
            <span className="text-terminal-muted">{analysis.news_impact}</span>
          </div>
          <div>
            <span className="text-terminal-label">Support : </span>
            <span className="text-terminal-green">{analysis.watch_levels.support.toLocaleString('en-IN')}</span>
            <span className="text-terminal-label ml-4">Resistance : </span>
            <span className="text-terminal-red">{analysis.watch_levels.resistance.toLocaleString('en-IN')}</span>
          </div>
          <div className="text-terminal-muted text-xs">
            Updated : {new Date(analysis.updated_at).toLocaleTimeString('en-IN')}
          </div>
        </div>
      )}
      <button
        onClick={onRefresh}
        className="mt-4 w-full border border-terminal-border text-terminal-label hover:text-terminal-text hover:border-terminal-blue text-xs py-1 rounded transition-colors"
      >
        [ Refresh Now ]
      </button>
    </div>
  )
}
```

- [ ] **Step 5: NewsFeed.tsx**

```tsx
// frontend/src/components/NewsFeed.tsx
import { useState } from 'react'
import type { NewsItem } from '../types'

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'text-terminal-green',
  negative: 'text-terminal-red',
  neutral:  'text-terminal-muted',
}
const SENTIMENT_DOT: Record<string, string> = {
  positive: 'bg-terminal-green',
  negative: 'bg-terminal-red',
  neutral:  'bg-terminal-muted',
}

export function NewsFeed({ news }: { news: NewsItem[] }) {
  const [region, setRegion] = useState<'all' | 'india' | 'global'>('all')
  const filtered = news.filter(n => region === 'all' || n.region === region)

  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 font-mono text-sm h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-3 border-b border-terminal-border pb-2">
        <span className="text-terminal-label text-xs tracking-widest">NEWS FEED</span>
        <div className="flex gap-1 text-xs">
          {(['all','india','global'] as const).map(r => (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`px-2 py-0.5 rounded border transition-colors ${
                region === r
                  ? 'border-terminal-blue text-terminal-blue'
                  : 'border-terminal-border text-terminal-muted hover:text-terminal-text'
              }`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {filtered.length === 0 && (
          <p className="text-terminal-muted text-xs">Loading news...</p>
        )}
        {filtered.map(item => (
          <a
            key={item.id}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block group"
          >
            <div className="flex items-start gap-2">
              <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${SENTIMENT_DOT[item.sentiment]}`} />
              <div>
                <p className={`text-xs leading-snug group-hover:underline ${SENTIMENT_COLOR[item.sentiment]}`}>
                  {item.title}
                </p>
                <p className="text-terminal-muted text-xs mt-0.5">
                  {item.source} · {new Date(item.published_at).toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit'})}
                </p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: MarketMoversStrip.tsx**

```tsx
// frontend/src/components/MarketMoversStrip.tsx
import type { MarketMovers } from '../types'

interface Mover { label: string; value: string; prefix?: string }

export function MarketMoversStrip({ movers }: { movers: MarketMovers | null }) {
  if (!movers) return null
  const items: Mover[] = [
    { label: 'USD/INR', value: movers.usdinr.toFixed(4) },
    { label: 'WTI',     value: movers.wti_crude.toFixed(2), prefix: '$' },
    { label: 'BRENT',   value: movers.brent_crude.toFixed(2), prefix: '$' },
    { label: 'GOLD',    value: movers.gold.toFixed(0), prefix: '$' },
    { label: 'VIX',     value: movers.vix.toFixed(2) },
    { label: 'US 10Y',  value: `${movers.us10y.toFixed(2)}%` },
    { label: 'MSCI',    value: movers.msci.toFixed(2) },
    { label: 'S&P 500', value: movers.sp500.toLocaleString('en-US', {maximumFractionDigits:0}) },
    ...(movers.sp500_futures ? [{ label: 'S&P FUT', value: movers.sp500_futures.toLocaleString('en-US', {maximumFractionDigits:0}) }] : []),
  ]
  return (
    <div className="w-full bg-terminal-panel border-t border-terminal-border px-4 py-2 flex gap-6 overflow-x-auto text-xs">
      {items.map(m => (
        <span key={m.label} className="flex gap-1 items-center whitespace-nowrap">
          <span className="text-terminal-label">{m.label}</span>
          <span className="text-terminal-text font-semibold">{m.prefix ?? ''}{m.value}</span>
        </span>
      ))}
    </div>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/
git commit -m "feat(frontend): all dashboard panel components"
```

---

## Task 13: App.tsx Wiring

**Files:**
- Rewrite: `frontend/src/App.tsx`

- [ ] **Step 1: Create App.tsx**

```tsx
// frontend/src/App.tsx
import { useWebSocket } from './hooks/useWebSocket'
import { MarketStatusBanner } from './components/MarketStatusBanner'
import { TickerBar }           from './components/TickerBar'
import { MLPredictionPanel }   from './components/MLPredictionPanel'
import { LLMAnalysisPanel }    from './components/LLMAnalysisPanel'
import { NewsFeed }            from './components/NewsFeed'
import { MarketMoversStrip }   from './components/MarketMoversStrip'

const WS_URL = 'ws://localhost:8000/ws'

export default function App() {
  const { message, status } = useWebSocket(WS_URL)

  const handleRefreshLLM = async () => {
    try {
      await fetch('/api/llm/refresh', { method: 'POST' })
    } catch { /* ignore */ }
  }

  return (
    <div className="flex flex-col h-screen bg-terminal-bg overflow-hidden">
      {/* Connection status */}
      {status !== 'connected' && (
        <div className="text-center text-xs py-0.5 bg-terminal-red/20 text-terminal-red">
          {status === 'connecting' ? 'Connecting...' : 'Reconnecting...'}
        </div>
      )}

      {/* Market status banner */}
      {message && <MarketStatusBanner status={message.market_status} />}

      {/* Ticker bar */}
      {message && <TickerBar indices={message.indices} />}

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-3 gap-2 p-2 overflow-hidden">
        <MLPredictionPanel pred={message?.ml_prediction ?? null} />
        <LLMAnalysisPanel
          analysis={message?.llm_analysis ?? null}
          onRefresh={handleRefreshLLM}
        />
        <NewsFeed news={message?.news ?? []} />
      </div>

      {/* Market movers strip */}
      <MarketMoversStrip movers={message?.market_movers ?? null} />
    </div>
  )
}
```

- [ ] **Step 2: Add LLM on-demand refresh endpoint to main.py**

Add to `backend/main.py` after the retrain endpoint:
```python
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
```

- [ ] **Step 3: Start both services and verify in browser**

Terminal 1:
```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — verify:
- Dark terminal UI loads
- Ticker bar shows index names (prices may be zero if markets closed, that's OK)
- ML Prediction panel shows "Training model..." or data
- Market movers strip appears at bottom
- WebSocket status shows "connected"

- [ ] **Step 4: Commit**

```bash
cd /Users/fighter/Documents/Projects_Folder/MarketAnalysis
git add frontend/src/App.tsx backend/main.py
git commit -m "feat: wire App.tsx with all panels and WebSocket feed"
```

---

## Task 14: Final Integration Test + .gitignore

**Files:**
- Create: `.gitignore`
- Create: `backend/tests/test_integration.py`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.pkl

# Database
backend/data/*.db

# Env
.env

# Node
frontend/node_modules/
frontend/dist/

# Superpowers
.superpowers/
```

- [ ] **Step 2: Write integration smoke test**

```python
# backend/tests/test_integration.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_ws_message_roundtrip():
    """Verify a WSMessage can be built from stubs and serialized cleanly."""
    from datetime import datetime, timezone
    from backend.models import WSMessage, MarketStatus, MarketMovers

    msg = WSMessage(
        type="market_update",
        timestamp=datetime.now(timezone.utc),
        market_status=MarketStatus(status="open"),
        indices=[],
        ml_prediction=None,
        llm_analysis=None,
        news=[],
        market_movers=MarketMovers(
            usdinr=84.5, wti_crude=78.0, brent_crude=80.0,
            gold=2300.0, vix=14.5, us10y=4.2, msci=145.0, sp500=5100.0,
        )
    )
    import json
    serialized = json.dumps(msg.model_dump(), default=str)
    parsed = json.loads(serialized)
    assert parsed["type"] == "market_update"
    assert parsed["market_status"]["status"] == "open"
```

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Full test run**

```bash
python -m pytest backend/tests/ -v --tb=short
```
Expected: All green.

- [ ] **Step 4: Final commit**

```bash
git add .gitignore backend/tests/test_integration.py
git commit -m "chore: gitignore + integration smoke test — MVP complete"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Covered In |
|---|---|
| Web app, browser-based | Task 10, 13 |
| Dhan API for Indian indices | Task 6 (fetch_dhan_quotes) |
| yfinance for global indices | Task 6 (fetch_yfinance_quotes) |
| NewsAPI + RSS news feed | Task 8 |
| Alpha Vantage / FRED | Not yet — add as incremental next step |
| 10-second polling | Task 6 (POLL_INTERVAL=10) |
| Futures mode during holidays | Task 5, 6 |
| ML Ridge Regression | Task 7 |
| Factor adjustments with rolling betas | Task 7 |
| Full prediction output matching screenshot | Task 7 |
| VIX range calculation | Task 7 |
| CV MAPE + directional accuracy | Task 7 |
| Logistic classifier AGREE/DISAGREE | Task 7 |
| LLM analysis with Claude API | Task 9 |
| 5-minute LLM refresh + on-demand | Task 9, 13 |
| Dark terminal aesthetic | Task 10, 12 |
| Ticker bar | Task 12 |
| ML Prediction panel (exact screenshot layout) | Task 12 |
| LLM Analysis panel | Task 12 |
| News feed with India/Global filter | Task 12 |
| Market movers strip | Task 12 |
| Market status banner | Task 12 |
| SQLite persistence | Task 3, 8, 9 |
| Model persistence (model.pkl) | Task 7 |
| /api/ml/retrain endpoint | Task 4 |

**Gap:** Alpha Vantage / FRED macro data not yet wired — add as next iteration after MVP works.
