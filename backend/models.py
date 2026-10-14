from pydantic import BaseModel
from typing import Optional, Literal, List
from datetime import datetime


class FIIDIIEntry(BaseModel):
    category:   str    # "FII/FPI" | "DII"
    date:       str
    # ── Cash market (₹ Crore) ─────────────────────────────────────────────────
    cash_buy:   float
    cash_sell:  float
    cash_net:   float
    # ── F&O — Index Futures (contracts) ──────────────────────────────────────
    fut_idx_long:  Optional[int] = None
    fut_idx_short: Optional[int] = None
    # ── F&O — Index Options (Call+Put Long / Short) ───────────────────────────
    opt_idx_long:  Optional[int] = None
    opt_idx_short: Optional[int] = None
    # ── F&O — Stock Futures (contracts) ──────────────────────────────────────
    fut_stk_long:  Optional[int] = None
    fut_stk_short: Optional[int] = None
    # ── Totals ────────────────────────────────────────────────────────────────
    total_long:    Optional[int] = None
    total_short:   Optional[int] = None


class FuturesContract(BaseModel):
    label:         str          # e.g. "NIFTY Apr", "GIFT NIFTY"
    expiry:        str          # e.g. "24-Apr-2025"
    price:         float
    change:        float
    change_pct:    float
    oi:            Optional[float] = None   # open interest
    is_gift:       bool = False
    is_prev_close: bool = False  # True = bhav copy (prev close), market closed


class StockMover(BaseModel):
    symbol: str
    name:   str = ""
    price:  float
    change: float
    change_pct: float


class IndexMovers(BaseModel):
    index_key:  str   # "nifty50" | "banknifty" | "midcap" | "sensex"
    gainers:    list[StockMover]
    losers:     list[StockMover]
    updated_at: datetime


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
    silver: Optional[float] = None
    vix: float
    us10y: float
    msci: float
    sp500: float
    sp500_futures: Optional[float] = None
    dow_futures:    Optional[float] = None
    nasdaq_futures: Optional[float] = None
    nikkei_futures: Optional[float] = None


class CryptoQuote(BaseModel):
    symbol:        str    # "BTC", "ETH", "SOL"
    name:          str    # "Bitcoin", etc.
    price_usd:     float
    change_pct_24h: float
    market_cap_usd: Optional[float] = None


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
    index_movers:   Optional[dict[str, IndexMovers]] = None
    nifty_futures:  Optional[list[FuturesContract]]  = None
    fii_dii:        Optional[list[FIIDIIEntry]]       = None
    crypto:         Optional[list[CryptoQuote]]       = None
