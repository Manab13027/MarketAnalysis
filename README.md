# Market Analysis

A **real-time stock-market analysis platform**. A FastAPI backend pulls live and
historical market data, aggregates financial news, runs lightweight ML and
AI-assisted analysis, and streams insights to a web frontend over WebSockets.

## Features
- Market data via `yfinance` and the Dhan broker API (`dhanhq`)
- News aggregation (NewsAPI + RSS via `feedparser`)
- ML signals (`scikit-learn`, `numpy`) and AI commentary (Anthropic)
- Real-time updates over WebSockets; SQLite storage (`aiosqlite`)
- FastAPI backend + separate frontend

## Stack
Python · FastAPI · WebSockets · scikit-learn · yfinance/Dhan · Anthropic

## Getting started
```bash
pip install -r requirements.txt
./start.sh          # backend on :8000, frontend on :5174
```

## Notes
- Add broker/news/AI API keys before running.
- For research only — **not financial advice**.
