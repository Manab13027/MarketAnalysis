# backend/news_engine.py
import asyncio, hashlib, os
from datetime import datetime, timezone
from typing import Optional

import feedparser
from newsapi import NewsApiClient

from backend.models import NewsItem

POSITIVE_WORDS = {
    "surge","rally","gain","rise","jump","bull","record","growth","profit",
    "beat","recovery","up","high","strong","positive","boost","soar",
}
NEGATIVE_WORDS = {
    "crash","fall","drop","plunge","sell","bear","loss","decline","weak",
    "fear","panic","down","low","recession","concern","risk","warning","selloff",
}
INDIA_KEYWORDS  = ["nifty","sensex","bse","nse","india","rbi","sebi","rupee","inr","dalal"]
GLOBAL_KEYWORDS = ["fed","s&p","nasdaq","dow","ecb","china","global","wall street","crude","oil","treasury"]

RSS_FEEDS = [
    ("https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2143429.cms", "Economic Times"),
    ("https://www.moneycontrol.com/rss/business.xml", "Moneycontrol"),
]


def tag_sentiment(title: str) -> str:
    lower = title.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
    if pos > neg:   return "positive"
    if neg > pos:   return "negative"
    return "neutral"


def tag_region(title: str) -> str:
    lower = title.lower()
    if any(w in lower for w in INDIA_KEYWORDS):
        return "india"
    return "global"


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


class NewsEngine:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
        self._client = NewsApiClient(api_key=self.api_key) if self.api_key else None

    def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        items.extend(self._fetch_newsapi())
        items.extend(self._fetch_rss())
        seen: set[str] = set()
        unique: list[NewsItem] = []
        for item in items:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)
        return sorted(unique, key=lambda x: x.published_at, reverse=True)[:30]

    def _fetch_newsapi(self) -> list[NewsItem]:
        if not self._client:
            return []
        try:
            resp = self._client.get_everything(
                q="NIFTY OR sensex OR stock market OR RBI OR Fed OR crude oil",
                language="en",
                sort_by="publishedAt",
                page_size=20,
            )
            items = []
            for a in resp.get("articles", []):
                title = a.get("title") or ""
                url   = a.get("url") or ""
                if not title or not url:
                    continue
                items.append(NewsItem(
                    id=_make_id(url),
                    title=title,
                    source=a.get("source", {}).get("name", ""),
                    url=url,
                    published_at=_parse_dt(a.get("publishedAt", "")),
                    sentiment=tag_sentiment(title),
                    region=tag_region(title),
                ))
            return items
        except Exception:
            return []

    def _fetch_rss(self) -> list[NewsItem]:
        items = []
        for feed_url, source_name in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title") or ""
                    url   = entry.get("link") or ""
                    if not title or not url:
                        continue
                    items.append(NewsItem(
                        id=_make_id(url),
                        title=title,
                        source=source_name,
                        url=url,
                        published_at=_parse_dt(entry.get("published", "")),
                        sentiment=tag_sentiment(title),
                        region=tag_region(title),
                    ))
            except Exception:
                continue
        return items


async def start_news_engine(app_state: dict, db_path: str) -> None:
    from backend.db import save_news_item
    engine = NewsEngine()
    while True:
        try:
            items = engine.fetch()
            app_state["latest_news"] = items
            for item in items:
                await save_news_item(db_path, {
                    "id": item.id, "title": item.title, "source": item.source,
                    "url": item.url, "published_at": item.published_at.isoformat(),
                    "sentiment": item.sentiment, "region": item.region,
                })
        except Exception as e:
            print(f"[news_engine] error: {e}")
        await asyncio.sleep(120)
