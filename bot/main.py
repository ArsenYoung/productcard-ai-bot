import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from .handlers import router


async def main():
    logging.basicConfig(level=logging.INFO)
    cfg = get_settings()
    if not cfg.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Укажи в .env или переменной окружения.")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(token=cfg.telegram_bot_token)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

