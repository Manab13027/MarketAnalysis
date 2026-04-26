# Market Analysis Dashboard — Design Spec
**Date:** 2026-04-26  
**Status:** Approved

---

## 1. Goal

A real-time web dashboard that analyzes Indian and global market indices, combining an ML-based next-day prediction engine with LLM-generated qualitative analysis, fed by live market data and news.

---

## 2. Architecture

```
React Frontend (Vite + TypeScript)
        │
        │  WebSocket  ws://localhost:8000/ws
        │  REST       http://localhost:8000/api/*
        │
FastAPI Backend (Python 3.11+)
        │
   ┌────┴──────────────────────────────────┐
   │           │              │            │
Data Engine  ML Engine   LLM Engine    SQLite DB
(10s poll)  (per tick)  (5min cycle)  (history +
                                       news cache)
```

### Data Engine — polls every 10 seconds
- **Dhan API** — NIFTY 50, SENSEX, Bank NIFTY spot prices (live during market hours)
- **yfinance** — S&P 500, NASDAQ, DAX, Nikkei 225, Hang Seng, USDINR, WTI crude, Brent crude, Gold, VIX, MSCI World ETF (EFA/VEA), US 10Y yield
- **Alpha Vantage / FRED** — macro indicators, FII/DII data supplement
- **NewsAPI + Google Finance RSS** — financial headlines, sentiment-tagged

### Holiday / After-Hours Mode
- Detects Indian market holidays via `holidays` Python library + NSE calendar
- When market closed: switches to **futures-only mode**
  - GIFT Nifty futures, S&P 500 futures (ES), Dow futures (YM), Nasdaq futures (NQ), Crude Oil futures, USDINR NDF
- Banner shown in UI: `MARKET CLOSED — Futures Mode`

---

## 3. ML Engine

### Model: Ridge Regression (scikit-learn)
Trained on 5 years of historical daily data fetched from yfinance.

**Target variable:** Next-day NIFTY 50 close

**Features (factors):**
| Factor | Source | Rolling Window |
|--------|--------|---------------|
| USDINR change % | yfinance | 15 days |
| USOIL (WTI) change % | yfinance | 15 days |
| MSCI World change % | yfinance (EFA — iShares MSCI EAFE ETF as proxy) | 1 month |
| Market Breadth (advance/decline ratio) | NSE website scrape / calculated from NIFTY 50 components via yfinance | 15 days |
| VIX level | yfinance (^VIX) | current |
| S&P 500 change % | yfinance | 15 days |

**Prediction output (per screenshot):**
```
[A] ML preliminary prediction       (Ridge base output)
[B] USDINR adjustment               (β × USDINR Δ, window=15d)
[C] USOIL adjustment                (β × USOIL Δ, window=15d)
[D] MSCI adjustment                 (β × MSCI Δ, window=1mo)
[E] BREADTH adjustment              (β × Breadth Δ, window=15d)
─────────────────────────────────────
FINAL PREDICTION                    (sum of above)
Expected move                       (Final - Today close, %)
Direction                           UP ▲ / DOWN ▼
P(UP)                               (classifier probability)
Classifier                          AGREE / DISAGREE + full/half move
Confidence                          (0.0 – 1.0)
VIX today                           (current VIX %)
VIX range                           (today close ± VIX-implied range)
Within VIX range?                   YES / NO
Factor today/predicted              (USDINR, USOIL, MSCI, BREADTH)
CV MAPE                             (cross-validated mean abs % error)
CV Dir Accuracy                     (cross-validated directional accuracy %)
```

### Classifier
A separate LogisticRegression classifier trained on same features predicts direction (UP/DOWN). If it agrees with Ridge direction → `AGREE`, else → `DISAGREE`. When disagree: output half the predicted move as conservative estimate.

### Model retraining
- Retrained automatically on app startup
- Manual retrain endpoint: `POST /api/ml/retrain`
- Model persisted to `data/model.pkl`

---

## 4. LLM Engine (Claude API)

**Trigger:** Every 5 minutes, or on-demand via UI button

**Prompt inputs:**
- Current ML prediction output (all factors, final prediction, direction)
- Top 10 news headlines (last 2 hours)
- Key macro values: USDINR, crude, VIX, S&P 500, FII/DII flows
- Market status (open/closed/holiday/futures-mode)

**Structured output:**
```json
{
  "bias": "BEARISH | BULLISH | NEUTRAL",
  "confidence": "HIGH | MEDIUM | LOW",
  "summary": "2-3 sentence plain English analysis",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "news_impact": "How today's news shifts the outlook",
  "watch_levels": { "support": 23800, "resistance": 24400 }
}
```

---

## 5. Frontend (React + Vite + TypeScript)

### Design
- **Theme:** Dark terminal aesthetic (`#0f1117` background, monospace font for data, green/red for direction)
- **Charts:** Recharts for sparklines and intraday charts

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  LIVE TICKER BAR  [NIFTY▲ SENSEX▼ BANKNIFTY▲ S&P▼ ...]  │
│  [MARKET CLOSED — FUTURES MODE banner when applicable]   │
├─────────────────────┬───────────────────┬────────────────┤
│  ML PREDICTION      │  LLM ANALYSIS     │  NEWS FEED     │
│  ─────────────────  │  ───────────────  │  ────────────  │
│  NIFTY 50           │  Bias: BEARISH    │ • Headline 1   │
│  Next-Day Pred      │  Confidence: MED  │ • Headline 2   │
│  23,853 ▼ DOWN      │                   │ • Headline 3   │
│                     │  Summary text...  │ • Headline 4   │
│  [A] ML base        │                   │ • Headline 5   │
│  [B] USDINR adj     │  Key Risks:       │                │
│  [C] USOIL adj      │  • Risk 1         │  [India] [Global]│
│  [D] MSCI adj       │  • Risk 2         │  filter tabs   │
│  [E] BREADTH adj    │                   │                │
│  ─────────────────  │  Watch levels:    │  Sentiment:    │
│  FINAL: 23,853      │  Support: 23,800  │  🟢 🔴 🟡 tags  │
│  Move: -319 (-1.3%) │  Resist: 24,400   │                │
│  P(UP): 0.40        │                   │                │
│  Classifier: AGREE  │  [Refresh Now]    │                │
│  Conf: 0.201        │                   │                │
│  VIX: 18.59%        │                   │                │
│  Range: 23840-24505 │                   │                │
│  CV MAPE: 1.25%     │                   │                │
│  CV DirAcc: 49.5%   │                   │                │
├─────────────────────┴───────────────────┴────────────────┤
│  MARKET MOVERS: USDINR 94.59 | WTI $95.49 | VIX 18.59   │
│                 GOLD $2,340  | US10Y 4.32% | MSCI 149.50 │
└──────────────────────────────────────────────────────────┘
```

### Panels
1. **Ticker Bar** — horizontal scroll, color-coded up/down, futures-mode aware
2. **ML Prediction Panel** — exact layout from screenshot, updates every 10s
3. **LLM Analysis Panel** — structured output, last-updated timestamp, manual refresh button
4. **News Feed Panel** — scrollable, India/Global filter, sentiment tags
5. **Market Movers Strip** — bottom bar, sparklines for each instrument

---

## 6. Data Model (SQLite)

```sql
predictions        -- ML outputs with timestamp (history)
market_data        -- Raw OHLCV snapshots every 10s
news_items         -- Headlines with sentiment + source
llm_analyses       -- LLM output history
model_metrics      -- CV MAPE, directional accuracy per retrain
```

---

## 7. Project Structure

```
MarketAnalysis/
├── backend/
│   ├── main.py                 # FastAPI app, WebSocket hub
│   ├── data_engine.py          # 10s polling, holiday detection, futures mode
│   ├── ml_engine.py            # Ridge + Classifier, training, prediction
│   ├── llm_engine.py           # Claude API integration
│   ├── news_engine.py          # NewsAPI + RSS fetcher
│   ├── db.py                   # SQLite schema + queries
│   ├── models.py               # Pydantic schemas
│   └── data/
│       ├── model.pkl           # Trained ML model
│       └── market.db           # SQLite database
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TickerBar.tsx
│   │   │   ├── MLPredictionPanel.tsx
│   │   │   ├── LLMAnalysisPanel.tsx
│   │   │   ├── NewsFeed.tsx
│   │   │   └── MarketMoversStrip.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
├── .env                        # API keys (Dhan, NewsAPI, Claude, Alpha Vantage)
└── requirements.txt
```

---

## 8. API Keys Required
- `DHAN_CLIENT_ID` + `DHAN_ACCESS_TOKEN` — Dhan API
- `NEWS_API_KEY` — NewsAPI
- `ANTHROPIC_API_KEY` — Claude API
- `ALPHA_VANTAGE_KEY` — Alpha Vantage (free tier sufficient)

---

## 9. Incremental Build Order
1. Backend scaffolding (FastAPI + WebSocket hub)
2. Data engine (yfinance first, then Dhan, then news)
3. ML engine (train on historical data, expose prediction)
4. Frontend skeleton (dark theme, WebSocket connection, ticker bar)
5. ML Prediction panel
6. LLM engine + Analysis panel
7. News feed panel
8. Market movers strip
9. Holiday / futures mode detection
10. SQLite persistence + history
