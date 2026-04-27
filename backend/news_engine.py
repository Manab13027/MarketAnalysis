import asyncio

async def start_news_engine(app_state: dict, db_path: str):
    while True:
        await asyncio.sleep(120)
