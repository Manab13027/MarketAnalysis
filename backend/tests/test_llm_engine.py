# backend/tests/test_llm_engine.py
from unittest.mock import patch, MagicMock

FAKE_LLM_RESPONSE = """{
  "bias": "BEARISH",
  "confidence": "MEDIUM",
  "summary": "Global cues remain weak with crude elevated and FII selling likely.",
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
