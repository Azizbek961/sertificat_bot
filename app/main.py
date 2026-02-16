import os
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .db import init_engine, create_tables
from .routers import all_routers


async def start_web_server() -> web.AppRunner:
    """
    Render Web Service port-scan uchun: 0.0.0.0:$PORT ga HTTP server ochib turadi.
    """
    port = int(os.getenv("PORT", "10000"))

    app = web.Application()

    async def health(_request):
        return web.Response(text="ok")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    return runner


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

    # ✅ Render uchun port ochamiz (bot bilan parallel ishlaydi)
    await start_web_server()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())