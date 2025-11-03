import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    llm_base_url: str
    llm_model: str
    llm_temperature: float
    llm_max_new_tokens: int
    db_path: str
    history_limit: int
    llm_timeout: float
    gen_max_retries: int
    gen_retry_delay_sec: float
    log_level: str
    cache_ttl_sec: float
    cache_size: int
    admin_ids: tuple[int, ...]
    log_file: str
    log_max_bytes: int
    log_backup_count: int
    backup_dir: str


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def get_settings() -> Settings:
    def _parse_admin_ids() -> tuple[int, ...]:
        raw = os.getenv("ADMIN_IDS", "").strip()
        if not raw:
            return tuple()
        out = []
        for part in raw.split(","):
            part = part.strip()
            # Trim surrounding quotes if provided in .env or Docker env-file
            if (part.startswith("'") and part.endswith("'")) or (
                part.startswith('"') and part.endswith('"')
            ):
                part = part[1:-1].strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except Exception:
                continue
        return tuple(out)

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        llm_model=os.getenv("LLM_MODEL", "phi3:mini"),
        llm_temperature=_float_env("LLM_TEMPERATURE", 0.6),
        llm_max_new_tokens=_int_env("LLM_MAX_NEW_TOKENS", 800),
        db_path=os.getenv("DB_PATH", "./data/bot.db"),
        history_limit=_int_env("HISTORY_LIMIT", 5),
        llm_timeout=_float_env("LLM_TIMEOUT", 120.0),
        gen_max_retries=_int_env("GEN_MAX_RETRIES", 2),
        gen_retry_delay_sec=_float_env("GEN_RETRY_DELAY_SEC", 0.5),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cache_ttl_sec=_float_env("CACHE_TTL_SEC", 600.0),
        cache_size=_int_env("CACHE_SIZE", 128),
        admin_ids=_parse_admin_ids(),
        log_file=os.getenv("LOG_FILE", "./logs/bot.log"),
        log_max_bytes=_int_env("LOG_MAX_BYTES", 1024 * 1024),
        log_backup_count=_int_env("LOG_BACKUP_COUNT", 5),
        backup_dir=os.getenv("BACKUP_DIR", "./backups"),
    )
