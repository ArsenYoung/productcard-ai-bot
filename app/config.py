import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_model: str
    llm_temperature: float
    llm_max_new_tokens: int


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
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        llm_model=os.getenv("LLM_MODEL", "phi3:mini"),
        llm_temperature=_float_env("LLM_TEMPERATURE", 0.6),
        llm_max_new_tokens=_int_env("LLM_MAX_NEW_TOKENS", 800),
    )

