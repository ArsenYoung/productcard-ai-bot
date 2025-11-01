import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from storage.sqlite_repo import init_db
from .handlers import router


async def main():
    cfg = get_settings()
    logging.basicConfig(level=getattr(logging, cfg.log_level.upper(), logging.INFO))
    if not cfg.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Provide it via .env or an environment variable.")

    # Init database
    await init_db(cfg.db_path)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(token=cfg.telegram_bot_token)
    logging.getLogger(__name__).info(
        "Starting bot: model=%s base_url=%s db=%s", cfg.llm_model, cfg.llm_base_url, cfg.db_path
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
