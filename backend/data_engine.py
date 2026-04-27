import asyncio
from typing import Any

async def start_data_engine(manager: Any, app_state: dict, db_path: str):
    while True:
        await asyncio.sleep(10)
