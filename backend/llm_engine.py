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
        self.api_key  = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._client  = anthropic.Anthropic(api_key=self.api_key)

    def analyze(
        self,
        ml_summary:     str,
        news_headlines: list[str],
        macro:          dict,
        market_status:  str,
    ) -> Optional[LLMAnalysis]:
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
                model="claude-sonnet-4-5",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
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
            payload = app_state.get("latest_payload") or {}
            ml_obj  = payload.get("ml_prediction")
            ml_summary = (
                f"NIFTY pred {ml_obj['final_prediction']} {ml_obj['direction']}, "
                f"P(UP)={ml_obj['p_up']}, Conf={ml_obj['confidence']}"
                if ml_obj else "ML prediction not available"
            )
            news      = app_state.get("latest_news", [])
            headlines = [
                (n.title if hasattr(n, "title") else n.get("title", ""))
                for n in news[:10]
            ]
            movers = payload.get("market_movers") or {}
            macro  = {
                "usdinr":    movers.get("usdinr", 0),
                "wti_crude": movers.get("wti_crude", 0),
                "vix":       movers.get("vix", 0),
                "sp500":     movers.get("sp500", 0),
            }
            status = (payload.get("market_status") or {}).get("status", "unknown")
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
