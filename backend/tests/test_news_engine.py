# backend/tests/test_news_engine.py
from unittest.mock import patch, MagicMock

def make_mock_article(title, source, url):
    return {
        "title": title,
        "source": {"name": source},
        "url": url,
        "publishedAt": "2026-04-26T08:00:00Z",
    }

@patch("backend.news_engine.feedparser.parse")
@patch("backend.news_engine.NewsApiClient")
def test_fetch_news_returns_news_items(mock_client_cls, mock_feedparser):
    from backend.news_engine import NewsEngine
    from backend.models import NewsItem
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_everything.return_value = {
        "articles": [
            make_mock_article("RBI holds rates steady", "Moneycontrol", "https://mc.com/1"),
            make_mock_article("Fed cuts unlikely in 2026", "Reuters", "https://reuters.com/1"),
        ]
    }
    mock_feedparser.return_value = MagicMock(entries=[])
    engine = NewsEngine(api_key="test")
    items = engine.fetch()
    assert len(items) == 2
    assert all(isinstance(i, NewsItem) for i in items)

def test_sentiment_tagging():
    from backend.news_engine import tag_sentiment
    assert tag_sentiment("Sensex surges 500 points on strong rally") == "positive"
    assert tag_sentiment("Market crash and panic sell-off fears") == "negative"
    assert tag_sentiment("RBI governor speech scheduled today") == "neutral"

def test_region_tagging():
    from backend.news_engine import tag_region
    assert tag_region("NIFTY 50 gains on positive cues") == "india"
    assert tag_region("Fed raises rates amid inflation concerns") == "global"
