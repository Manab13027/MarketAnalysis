# backend/tests/test_integration.py
import json
import pytest
from datetime import datetime, timezone
from backend.models import WSMessage, MarketStatus, MarketMovers


@pytest.mark.asyncio
async def test_ws_message_roundtrip():
    """Full WSMessage serializes and deserializes cleanly — covers the complete data contract."""
    msg = WSMessage(
        type="market_update",
        timestamp=datetime.now(timezone.utc),
        market_status=MarketStatus(status="open"),
        indices=[],
        ml_prediction=None,
        llm_analysis=None,
        news=[],
        market_movers=MarketMovers(
            usdinr=84.5, wti_crude=78.0, brent_crude=80.0,
            gold=2300.0, vix=14.5, us10y=4.2, msci=145.0, sp500=5100.0,
        )
    )
    serialized = json.dumps(msg.model_dump(), default=str)
    parsed = json.loads(serialized)
    assert parsed["type"] == "market_update"
    assert parsed["market_status"]["status"] == "open"
    assert parsed["market_movers"]["usdinr"] == 84.5
    assert parsed["ml_prediction"] is None
    assert parsed["llm_analysis"] is None


def test_market_status_futures_mode_roundtrip():
    """Futures mode message serializes correctly."""
    msg = WSMessage(
        type="market_update",
        timestamp=datetime.now(timezone.utc),
        market_status=MarketStatus(status="futures_mode", message="MARKET CLOSED — Futures Mode"),
        indices=[],
        ml_prediction=None,
        llm_analysis=None,
        news=[],
        market_movers=MarketMovers(
            usdinr=84.5, wti_crude=78.0, brent_crude=80.0,
            gold=2300.0, vix=14.5, us10y=4.2, msci=145.0, sp500=5100.0,
        )
    )
    data = msg.model_dump()
    assert data["market_status"]["status"] == "futures_mode"
    assert data["market_status"]["message"] == "MARKET CLOSED — Futures Mode"
