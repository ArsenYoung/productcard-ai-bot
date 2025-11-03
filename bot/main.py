import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from storage.sqlite_repo import init_db
from .handlers import router


async def main():
    cfg = get_settings()
    # Configure logging: console + optional rotating file
    root_level = getattr(logging, str(getattr(cfg, 'log_level', 'INFO')).upper(), logging.INFO)
    logging.basicConfig(level=root_level)
    log_file = getattr(cfg, 'log_file', None)
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
            handler = RotatingFileHandler(
                log_file,
                maxBytes=getattr(cfg, 'log_max_bytes', 1024 * 1024),
                backupCount=getattr(cfg, 'log_backup_count', 5),
                encoding='utf-8'
            )
            handler.setLevel(root_level)
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
            logging.getLogger().addHandler(handler)
        except Exception:
            # Do not fail startup on logging setup errors
            pass
    if not cfg.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Provide it via .env or an environment variable.")

    # Init database
    await init_db(cfg.db_path)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(token=cfg.telegram_bot_token)
    logging.getLogger(__name__).info(
        "Starting bot: model=%s base_url=%s db=%s admins=%s",
        cfg.llm_model,
        cfg.llm_base_url,
        cfg.db_path,
        ",".join(str(i) for i in getattr(cfg, "admin_ids", tuple())) or "-",
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
