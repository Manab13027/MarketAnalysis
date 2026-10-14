# backend/telegram_feed.py
"""
Fetches latest posts from configured Telegram channels using Telethon (MTProto).
MTProto uses Telegram's own protocol (not the blocked t.me web), so it works
even when the web preview is inaccessible.

Setup (one-time):
  1. Get API_ID + API_HASH from https://my.telegram.org → API development tools
  2. Run: python scripts/gen_telegram_session.py  → paste SESSION_STRING into .env
  3. Add to .env:
       TELEGRAM_API_ID=12345678
       TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
       TELEGRAM_SESSION=1BQANOTEuMjA4...  (output of gen script)
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

TELEGRAM_CHANNELS = [
    "lmwmnews",
]

_items_cache: list[dict] = []


async def fetch_telegram_posts(limit: int = 20) -> list[dict]:
    """
    Returns list of dicts: {title, url, published_at, source}
    Returns [] if Telegram credentials are not configured.
    """
    api_id      = os.getenv("TELEGRAM_API_ID", "")
    api_hash    = os.getenv("TELEGRAM_API_HASH", "")
    session_str = os.getenv("TELEGRAM_SESSION", "")

    if not (api_id and api_hash and session_str):
        return []

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        client = TelegramClient(StringSession(session_str), int(api_id), api_hash)
        await client.connect()

        posts: list[dict] = []
        for channel_username in TELEGRAM_CHANNELS:
            try:
                entity   = await client.get_entity(channel_username)
                messages = await client.get_messages(entity, limit=limit)
                for msg in messages:
                    text = (msg.message or "").strip()
                    if not text:
                        continue
                    # Use first line as title (up to 200 chars)
                    title = text.split("\n")[0][:200] or text[:200]
                    pub   = msg.date
                    if pub and pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    posts.append({
                        "title":        title,
                        "url":          f"https://t.me/{channel_username}/{msg.id}",
                        "published_at": pub or datetime.now(timezone.utc),
                        "source":       f"Telegram @{channel_username}",
                    })
            except Exception as e:
                print(f"[telegram_feed] channel {channel_username} error: {e}")

        await client.disconnect()
        return posts

    except Exception as e:
        print(f"[telegram_feed] error: {e}")
        return []
