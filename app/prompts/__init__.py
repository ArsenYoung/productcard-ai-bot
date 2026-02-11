import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional


_PROMPTS_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("productcard")


@lru_cache(maxsize=None)
def _read_raw(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def _split_sections(raw: str) -> dict[str, str]:
    """Parse [lang] sections into a dict."""
    sections: dict[str, str] = {}
    current = "default"
    buf: list[str] = []
    for line in raw.splitlines():
        m = re.match(r"\[(\w+)\]\s*$", line.strip())
        if m:
            if buf:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).lower()
            buf = []
            continue
        buf.append(line)
    if buf:
        sections[current] = "\n".join(buf).strip()
    return {k: v for k, v in sections.items() if v}


def load_prompt(name: str, *, language: Optional[str] = None, default: str = "") -> str:
    """Load prompt text from app/prompts/<name>.txt with optional [lang] blocks.

    Falls back to the provided default string if file is missing or empty.
    """
    try:
        raw = _read_raw(name)
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s.txt; using default", name)
        return default
    except Exception as e:
        logger.warning("Failed to read prompt %s: %s", name, e)
        return default

    if not raw.strip():
        return default

    if language:
        sections = _split_sections(raw)
        lang_key = language.lower()
        if sections:
            return sections.get(lang_key) or sections.get("default") or default or raw

    return raw
