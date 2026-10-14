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
  gold: number; silver: number | null; vix: number; us10y: number; msci: number;
  sp500: number; sp500_futures: number | null;
  dow_futures: number | null; nasdaq_futures: number | null; nikkei_futures: number | null;
}
export interface CryptoQuote {
  symbol: string;       // "BTC", "ETH", "SOL"
  name: string;
  price_usd: number;
  change_pct_24h: number;
  market_cap_usd: number | null;
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
export interface FIIDIIEntry {
  category: string; date: string;
  cash_buy: number; cash_sell: number; cash_net: number;
  fut_idx_long:  number | null; fut_idx_short:  number | null;
  opt_idx_long:  number | null; opt_idx_short:  number | null;
  fut_stk_long:  number | null; fut_stk_short:  number | null;
  total_long:    number | null; total_short:    number | null;
}
export interface FuturesContract {
  label: string; expiry: string;
  price: number; change: number; change_pct: number;
  oi: number | null; is_gift: boolean; is_prev_close: boolean;
}
export interface WSMessage {
  type: "market_update" | "error";
  timestamp: string; market_status: MarketStatus;
  indices: IndexQuote[]; ml_prediction: MLPrediction | null;
  llm_analysis: LLMAnalysis | null; news: NewsItem[];
  market_movers: MarketMovers;
  index_movers?: Record<string, IndexMovers>;
  nifty_futures?: FuturesContract[] | null;
  fii_dii?: FIIDIIEntry[] | null;
  crypto?: CryptoQuote[] | null;
}
