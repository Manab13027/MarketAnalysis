# backend/tests/test_ml_engine.py
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch


def make_fake_history(n=300):
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    np.random.seed(42)
    nifty  = 20000 + np.cumsum(np.random.randn(n) * 100)
    usdinr = 83    + np.cumsum(np.random.randn(n) * 0.1)
    usoil  = 80    + np.cumsum(np.random.randn(n) * 0.5)
    msci   = 65    + np.cumsum(np.random.randn(n) * 0.3)
    vix    = 15    + np.abs(np.random.randn(n) * 2)
    sp500  = 4500  + np.cumsum(np.random.randn(n) * 20)
    return pd.DataFrame(
        {"nifty": nifty, "usdinr": usdinr, "usoil": usoil,
         "msci": msci, "vix": vix, "sp500": sp500},
        index=dates,
    )


@patch("backend.ml_engine.MLEngine._fetch_historical_data")
def test_train_produces_metrics(mock_fetch):
    from backend.ml_engine import MLEngine
    mock_fetch.return_value = make_fake_history(300)
    ml = MLEngine(db_path=":memory:")
    ml.train()
    assert 0 < ml.cv_mape < 20        # MAPE under 20%
    assert 0 < ml.cv_dir_accuracy <= 1.0


@patch("backend.ml_engine.MLEngine._fetch_historical_data")
def test_predict_returns_ml_prediction(mock_fetch):
    from backend.ml_engine import MLEngine
    from backend.models import MLPrediction
    mock_fetch.return_value = make_fake_history(300)
    ml = MLEngine(db_path=":memory:")
    ml.train()
    pred = ml.predict(usdinr=94.55, usoil=95.49, msci=149.50, vix=18.59, sp500=5218.0)
    assert isinstance(pred, MLPrediction)
    assert pred.direction in ("UP", "DOWN")
    assert 0.0 <= pred.p_up <= 1.0
    assert pred.cv_mape > 0
    assert pred.final_prediction > 0
    # All 4 adjustment keys present
    assert set(pred.adjustments.keys()) == {"usdinr", "usoil", "msci", "breadth"}
    # All 4 factor today/pred keys present
    assert set(pred.factors_today_pred.keys()) == {"usdinr", "usoil", "msci", "breadth"}
