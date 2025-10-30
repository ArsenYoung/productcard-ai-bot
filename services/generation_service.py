import json
import logging
import re
import asyncio
from typing import Any, Dict, Optional

from app.config import get_settings
from app.platforms import get_profile, LENGTH_HINTS, TONE_LABELS
from .llm_client import OllamaClient


SYSTEM_PROMPT = (
    "You are an assistant that writes concise, compelling e-commerce product cards. "
    "Always return strict, valid JSON with keys: title, short_description, bullets (array of strings). "
    "No markdown, no extra text besides JSON."
)

REPAIR_SYSTEM_PROMPT = (
    "You fix and normalize outputs to strict JSON. "
    "Return only valid JSON with keys: title, short_description, bullets (array of strings). "
    "No commentary, no markdown."
)

logger = logging.getLogger("productcard")


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        chunk = m.group(0)
        try:
            return json.loads(chunk)
        except Exception:
            pass

    return {
        "title": "",
        "short_description": text.strip(),
        "bullets": [],
    }


def build_product_prompt(
    *,
    product_name: str,
    features: Optional[str] = None,
    audience: Optional[str] = None,
    platform: Optional[str] = None,
    tone: str = "neutral",
    length: str = "medium",
) -> str:
    parts = []
    profile = get_profile(platform)
    if platform:
        parts.append(f"Platform: {platform}")
    parts.append(f"Product name: {product_name}")
    parts.append(f"Tone: {TONE_LABELS.get(tone, tone)}")
    if audience:
        parts.append(f"Target audience: {audience}")
    if features:
        parts.append(f"Key features/specs: {features}")
    # Derived length target (capped by platform profile limits)
    target_desc = min(LENGTH_HINTS.get(length, 300), profile.description_max)
    parts.append(
        "Output strict JSON with fields: title, short_description, bullets (array)."
    )
    parts.append(
        f"Constraints: title <= {profile.title_max} chars; short_description <= {target_desc} chars; "
        f"bullets {profile.bullets_min}-{profile.bullets_max} items; no markdown; no extra text."
    )
    return "\n".join(parts)


async def generate_product_card(
    *,
    product_name: str,
    features: Optional[str] = None,
    audience: Optional[str] = None,
    platform: Optional[str] = None,
    tone: str = "neutral",
    length: str = "medium",
    temperature: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    cfg = get_settings()
    client = OllamaClient(base_url=cfg.llm_base_url, model=cfg.llm_model)

    temperature = temperature if temperature is not None else cfg.llm_temperature
    max_new_tokens = max_new_tokens if max_new_tokens is not None else cfg.llm_max_new_tokens

    prompt = build_product_prompt(
        product_name=product_name,
        features=features,
        audience=audience,
        platform=platform,
        tone=tone,
        length=length,
    )

    attempt = 0
    last_raw = ""
    payload: Dict[str, Any] = {}
    while True:
        attempt += 1
        raw = await client.generate(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            stop=["\n\n"],
            timeout=cfg.llm_timeout,
        )
        last_raw = raw
        payload = _extract_json(raw)
        # Validate essential structure
        if isinstance(payload.get("title"), str) and isinstance(payload.get("short_description"), str) and isinstance(payload.get("bullets"), (list, tuple)):
            break

        if attempt > cfg.gen_max_retries:
            logger.warning("JSON invalid after %s attempts; returning best-effort parse", attempt)
            break

        # Repair attempt: ask the model to fix into JSON
        logger.info("Retrying generation with repair (attempt %s)", attempt)
        repair_prompt = (
            "Convert the following text into strict JSON with keys: title, short_description, bullets (array).\n"
            "Only output the JSON.\n\nText:\n" + last_raw
        )
        await asyncio.sleep(cfg.gen_retry_delay_sec)
        raw = await client.generate(
            repair_prompt,
            system=REPAIR_SYSTEM_PROMPT,
            temperature=0.2,
            max_new_tokens=max_new_tokens,
            stop=["\n\n"],
            timeout=cfg.llm_timeout,
        )
        payload = _extract_json(raw)
        if isinstance(payload.get("title"), str) and isinstance(payload.get("short_description"), str) and isinstance(payload.get("bullets"), (list, tuple)):
            break
        await asyncio.sleep(cfg.gen_retry_delay_sec)
    # Postprocess to enforce limits just in case
    profile = get_profile(platform)
    title = str(payload.get("title", ""))[: profile.title_max].strip()
    desc = str(payload.get("short_description", ""))[: profile.description_max].strip()
    bullets = payload.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = []
    bullets = [str(b).strip() for b in bullets if str(b).strip()]
    bullets = bullets[: profile.bullets_max]
    if len(bullets) < profile.bullets_min:
        # best-effort: duplicate trimmed bullets to reach min length if possible
        while bullets and len(bullets) < profile.bullets_min:
            bullets.append(bullets[len(bullets) % len(bullets)])
    payload.update(title=title, short_description=desc, bullets=bullets)
    return payload
