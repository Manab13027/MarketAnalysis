from backend.models import (
    FactorAdjustment, FactorTodayPred, MLPrediction,
    IndexQuote, MarketMovers, NewsItem, LLMAnalysis,
    MarketStatus, WSMessage
)
from datetime import datetime, timezone

def test_ml_prediction_construction():
    pred = MLPrediction(
        today_close=24173.05,
        ml_preliminary=24002.25,
        adjustments={
            "usdinr": FactorAdjustment(value=-56.31, beta=-1.5539, window="15d"),
            "usoil": FactorAdjustment(value=-38.92, beta=-0.1382, window="15d"),
            "msci": FactorAdjustment(value=-43.79, beta=0.9341, window="1mo"),
            "breadth": FactorAdjustment(value=-10.06, beta=0.0204, window="15d"),
        },
        final_prediction=23853.18,
        expected_move=-319.87,
        expected_move_pct=-1.32,
        direction="DOWN",
        p_up=0.400,
        classifier="AGREE",
        classifier_detail="full move",
        confidence=0.201,
        vix_today=18.59,
        vix_range_low=23840.41,
        vix_range_high=24505.69,
        within_vix_range=True,
        factors_today_pred={
            "usdinr": FactorTodayPred(today=94.5485, pred=94.6902, direction="UP"),
            "usoil": FactorTodayPred(today=95.49, pred=96.61, direction="UP"),
            "msci": FactorTodayPred(today=149.50, pred=149.21, direction="DOWN"),
            "breadth": FactorTodayPred(today=0.880, pred=0.862, direction="DOWN"),
        },
        cv_mape=1.25,
        cv_dir_accuracy=49.5,
    )
    assert pred.final_prediction == 23853.18
    assert pred.direction == "DOWN"

def test_ws_message_serializes():
    msg = WSMessage(
        type="market_update",
        timestamp=datetime.now(timezone.utc),
        market_status=MarketStatus(status="open", message=None),
        indices=[],
        ml_prediction=None,
        llm_analysis=None,
        news=[],
        market_movers=MarketMovers(
            usdinr=94.59, wti_crude=95.49, brent_crude=96.1,
            gold=2340.0, vix=18.59, us10y=4.32, msci=149.50, sp500=5218.0,
            sp500_futures=None,
        )
    )
    data = msg.model_dump()
    assert data["type"] == "market_update"
