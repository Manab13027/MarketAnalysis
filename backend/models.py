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
