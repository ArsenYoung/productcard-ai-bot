import json
import re
from typing import Any, Dict, Optional

from app.config import get_settings
from .llm_client import OllamaClient


SYSTEM_PROMPT = (
    "You are an assistant that writes concise, compelling e-commerce product cards. "
    "Always return strict, valid JSON with keys: title, short_description, bullets (array of strings). "
    "No markdown, no extra text besides JSON."
)


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
) -> str:
    parts = []
    if platform:
        parts.append(f"Platform: {platform}")
    parts.append(f"Product name: {product_name}")
    parts.append(f"Tone: {tone}")
    if audience:
        parts.append(f"Target audience: {audience}")
    if features:
        parts.append(f"Key features/specs: {features}")
    parts.append(
        "Output JSON with fields: title (<=70 chars), short_description (<=300 chars), bullets (3-6 items)."
    )
    return "\n".join(parts)


async def generate_product_card(
    *,
    product_name: str,
    features: Optional[str] = None,
    audience: Optional[str] = None,
    platform: Optional[str] = None,
    tone: str = "neutral",
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
    )

    raw = await client.generate(
        prompt,
        system=SYSTEM_PROMPT,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        stop="\n\n",
    )
    return _extract_json(raw)

