import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .db import init_engine, create_tables
from .routers import all_routers

async def main():
    config = load_config()

    sessionmaker = init_engine(config.db_url)
    await create_tables()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # dependency injection
    dp["config"] = config
    dp["sessionmaker"] = sessionmaker

    for r in all_routers:
        dp.include_router(r)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())