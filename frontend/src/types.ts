export interface FactorAdjustment {
  value: number; beta: number; window: string;
}
export interface FactorTodayPred {
  today: number; pred: number; direction: "UP" | "DOWN";
}
export interface MLPrediction {
  today_close: number; ml_preliminary: number;
  adjustments: Record<string, FactorAdjustment>;
  final_prediction: number; expected_move: number; expected_move_pct: number;
  direction: "UP" | "DOWN"; p_up: number;
  classifier: "AGREE" | "DISAGREE"; classifier_detail: string;
  confidence: number; vix_today: number;
  vix_range_low: number; vix_range_high: number; within_vix_range: boolean;
  factors_today_pred: Record<string, FactorTodayPred>;
  cv_mape: number; cv_dir_accuracy: number;
}
export interface IndexQuote {
  symbol: string; name: string; price: number;
  change: number; change_pct: number; is_futures: boolean;
}
export interface MarketMovers {
  usdinr: number; wti_crude: number; brent_crude: number;
  gold: number; vix: number; us10y: number; msci: number;
  sp500: number; sp500_futures: number | null;
}
export interface NewsItem {
  id: string; title: string; source: string; url: string;
  published_at: string;
  sentiment: "positive" | "negative" | "neutral";
  region: "india" | "global";
}
export interface LLMAnalysis {
  bias: "BULLISH" | "BEARISH" | "NEUTRAL";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  summary: string; key_risks: string[]; news_impact: string;
  watch_levels: { support: number; resistance: number };
  updated_at: string;
}
export interface MarketStatus {
  status: "open" | "closed" | "holiday" | "futures_mode" | "pre_open";
  message: string | null;
}
export interface StockMover {
  symbol: string
  name:   string
  price:  number
  change: number
  change_pct: number
}
export interface IndexMovers {
  index_key: string
  gainers:   StockMover[]
  losers:    StockMover[]
  updated_at: string
}
export interface WSMessage {
  type: "market_update" | "error";
  timestamp: string; market_status: MarketStatus;
  indices: IndexQuote[]; ml_prediction: MLPrediction | null;
  llm_analysis: LLMAnalysis | null; news: NewsItem[];
  market_movers: MarketMovers;
  index_movers?: Record<string, IndexMovers>
}
