# backend/tests/test_db.py
import pytest

@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")

@pytest.mark.asyncio
async def test_init_and_insert_prediction(tmp_db):
    from backend.db import init_db, save_prediction, get_recent_predictions
    await init_db(tmp_db)
    row = {
        "timestamp": "2026-04-26T10:00:00+00:00",
        "today_close": 24173.05,
        "final_prediction": 23853.18,
        "direction": "DOWN",
        "p_up": 0.40,
        "cv_mape": 1.25,
        "cv_dir_accuracy": 49.5,
    }
    await save_prediction(tmp_db, row)
    rows = await get_recent_predictions(tmp_db, limit=5)
    assert len(rows) == 1
    assert rows[0]["direction"] == "DOWN"
