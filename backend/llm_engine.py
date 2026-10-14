# backend/llm_engine.py
import asyncio, json, os, time
from datetime import datetime, timezone
from typing import Optional

import anthropic
import httpx

from backend.models import LLMAnalysis

# Alpha Vantage macro snapshot cache (module-level)
_av_snapshot: dict = {}
_av_last_fetch: float = 0.0
AV_REFRESH_INTERVAL = 7200  # 2 hours

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


OLLAMA_BASE    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL",   "qwen2.5:14b")


class LLMEngine:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key  = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._client  = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def _call_ollama(self, user_msg: str) -> Optional[str]:
        """Call local Ollama instance. Returns raw text or None."""
        # First warm up the model (keep-alive ping) then do the real call
        try:
            httpx.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": "", "keep_alive": "10m"},
                timeout=30.0,
            )
        except Exception:
            pass  # non-fatal — just speeds up the main call
        try:
            r = httpx.post(
                f"{OLLAMA_BASE}/api/chat",
                json={
                    "model":    OLLAMA_MODEL,
                    "messages": [
                        {"role": "system",  "content": SYSTEM_PROMPT},
                        {"role": "user",    "content": user_msg},
                    ],
                    "stream":  False,
                    "format":  "json",
                    "options": {"temperature": 0.3},
                },
                timeout=180.0,   # 3 min — large models need time on first load
            )
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as e:
            print(f"[llm_engine] ollama error: {e}")
            return None

    def _call_anthropic(self, user_msg: str) -> Optional[str]:
        """Call Anthropic API. Returns raw text or None."""
        if not self._client:
            return None
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[llm_engine] anthropic error: {e}")
            return None

    def analyze(
        self,
        ml_summary:     str,
        news_headlines: list[str],
        macro:          dict,
        market_status:  str,
        macro_av:       dict = {},
    ) -> Optional[LLMAnalysis]:
        news_block = "\n".join(f"• {h}" for h in news_headlines[:10])

        av_block = ""
        if macro_av:
            sp500_av  = macro_av.get("sp500")
            nasdaq_av = macro_av.get("nasdaq")
            usdinr_av = macro_av.get("usdinr")
            parts = []
            if sp500_av:
                parts.append(f"- S&P 500 (SPY): {sp500_av.get('price', 'N/A')} ({sp500_av.get('change_pct', 'N/A'):+.2f}%)")
            if nasdaq_av:
                parts.append(f"- NASDAQ (QQQ): {nasdaq_av.get('price', 'N/A')} ({nasdaq_av.get('change_pct', 'N/A'):+.2f}%)")
            if usdinr_av:
                parts.append(f"- USD/INR: {usdinr_av}")
            if parts:
                fetched = macro_av.get("fetched_at", "")
                av_block = "\nAlpha Vantage Macro Data (as of {}):\n{}".format(
                    fetched, "\n".join(parts)
                )

        user_msg = f"""Market Status: {market_status}

ML Prediction:
{ml_summary}

Macro Snapshot:
- USD/INR: {macro.get('usdinr', 'N/A')}
- WTI Crude: ${macro.get('wti_crude', 'N/A')}
- VIX: {macro.get('vix', 'N/A')}
- S&P 500: {macro.get('sp500', 'N/A')}
{av_block}
Recent Headlines:
{news_block}

Produce the JSON analysis now."""

        # Try Ollama first (free, local), fall back to Anthropic
        raw = self._call_ollama(user_msg) or self._call_anthropic(user_msg)
        if not raw:
            return None
        try:
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
            print(f"[llm_engine] parse error: {e} — raw: {raw[:200]}")
            return None


async def start_llm_engine(app_state: dict, db_path: str) -> None:
    from backend.db import save_llm_analysis
    from backend.alpha_vantage_client import fetch_macro_snapshot

    global _av_snapshot, _av_last_fetch

    engine = LLMEngine()
    await asyncio.sleep(30)  # wait for data_engine + ML to populate app_state first
    while True:
        # Refresh Alpha Vantage macro snapshot every 2 hours
        now = time.monotonic()
        if now - _av_last_fetch > AV_REFRESH_INTERVAL:
            try:
                loop = asyncio.get_running_loop()
                snapshot = await loop.run_in_executor(None, fetch_macro_snapshot)
                if snapshot:
                    _av_snapshot = snapshot
                    _av_last_fetch = now
            except Exception as exc:
                print(f"[llm_engine] alpha_vantage snapshot error: {exc}")

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
            loop = asyncio.get_running_loop()
            analysis = await loop.run_in_executor(
                None, engine.analyze, ml_summary, headlines, macro, status, _av_snapshot
            )
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

        await asyncio.sleep(300)  # then every 5 minutes
