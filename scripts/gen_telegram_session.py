"""
One-time script to generate a Telethon StringSession for use in .env.

Usage:
  python scripts/gen_telegram_session.py

You'll need:
  - TELEGRAM_API_ID   (from https://my.telegram.org → API development tools)
  - TELEGRAM_API_HASH (same page)

The script will ask for your phone number and the code Telegram sends you,
then print the SESSION_STRING. Paste it into your .env file.

This only needs to be run ONCE. The session string works indefinitely.
"""
import asyncio


async def main():
    api_id   = input("Enter TELEGRAM_API_ID (number): ").strip()
    api_hash = input("Enter TELEGRAM_API_HASH: ").strip()

    from telethon import TelegramClient
    from telethon.sessions import StringSession

    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.start()

    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("Add this to your .env file:")
    print(f"TELEGRAM_API_ID={api_id}")
    print(f"TELEGRAM_API_HASH={api_hash}")
    print(f"TELEGRAM_SESSION={session_string}")
    print("=" * 60)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
