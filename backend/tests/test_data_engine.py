# backend/tests/test_data_engine.py
import pytest
from unittest.mock import patch, MagicMock

def make_mock_ticker(price: float, prev_close: float):
    mock = MagicMock()
    mock.fast_info = MagicMock()
    mock.fast_info.last_price = price
    mock.fast_info.previous_close = prev_close
    return mock

@patch("backend.data_engine.yf.Tickers")
def test_fetch_yfinance_quotes_returns_index_quotes(mock_tickers):
    from backend.data_engine import fetch_yfinance_quotes
    from backend.models import IndexQuote
    tickers_obj = MagicMock()
    tickers_obj.tickers = {
        "^GSPC": make_mock_ticker(5218.0, 5200.0),
        "^IXIC": make_mock_ticker(16300.0, 16200.0),
    }
    mock_tickers.return_value = tickers_obj
    quotes = fetch_yfinance_quotes([("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ")])
    assert len(quotes) == 2
    assert all(isinstance(q, IndexQuote) for q in quotes)
    assert quotes[0].price == 5218.0
    assert abs(quotes[0].change_pct - (5218.0 - 5200.0) / 5200.0 * 100) < 0.01

@patch("backend.data_engine.yf.Tickers")
def test_fetch_market_movers_returns_market_movers(mock_tickers):
    from backend.data_engine import fetch_market_movers
    from backend.models import MarketMovers
    tickers_obj = MagicMock()
    tickers_obj.tickers = {}
    for sym in ["USDINR=X","CL=F","BZ=F","GC=F","^VIX","^TNX","EFA","^GSPC","ES=F"]:
        tickers_obj.tickers[sym] = make_mock_ticker(100.0, 99.0)
    mock_tickers.return_value = tickers_obj
    movers = fetch_market_movers()
    assert isinstance(movers, MarketMovers)
    assert movers.usdinr == 100.0
