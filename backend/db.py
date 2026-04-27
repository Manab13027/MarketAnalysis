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
