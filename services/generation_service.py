import json
import logging
import re
import asyncio
from typing import Any, Dict, Optional, Tuple, Callable, Awaitable

from app.config import get_settings
from app.platforms import get_profile, LENGTH_HINTS, TONE_LABELS
from .llm_client import OllamaClient


SYSTEM_PROMPT_EN = (
    "You are an assistant that writes concise, compelling e-commerce product cards. "
    "Always return strict, valid JSON with keys: title, short_description, bullets (array of strings). "
    "No markdown, no code fences, no extra text besides JSON."
)

SYSTEM_PROMPT_RU = (
    "Ты ассистент, который пишет краткие и убедительные карточки товара для маркетплейсов. "
    "Пиши ТОЛЬКО на русском языке. "
    "Возвращай СТРОГО валидный JSON со свойствами: title, short_description, bullets (массив строк). "
    "Без markdown и без тройных кавычек/код‑блоков. Никакого лишнего текста, только JSON."
)

REPAIR_SYSTEM_PROMPT_EN = (
    "You fix and normalize outputs to strict JSON only. "
    "Return only valid JSON with keys: title, short_description, bullets (array of strings). "
    "No commentary, no markdown."
)

REPAIR_SYSTEM_PROMPT_RU = (
    "Преобразуй текст в СТРОГИЙ JSON. "
    "Верни только валидный JSON со свойствами: title, short_description, bullets (массив строк). "
    "Никаких комментариев, markdown или лишнего текста."
)

logger = logging.getLogger("productcard")

# Simple in-memory cache with TTL
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_ORDER: list[str] = []

def _cache_key(**kwargs: Any) -> str:
    # Normalize values and build a stable key
    parts = [
        str(kwargs.get("product_name", "")).strip().lower(),
        str(kwargs.get("features", "")).strip().lower(),
        str(kwargs.get("platform", "")).strip().lower(),
        str(kwargs.get("tone", "")).strip().lower(),
        str(kwargs.get("length", "")).strip().lower(),
        str(kwargs.get("language", "")).strip().lower(),
    ]
    return "|".join(parts)


def _extract_json(text: str) -> Dict[str, Any]:
    """Best‑effort extraction of a JSON object from model output.

    Tolerates code fences and trailing commas; if everything fails, returns
    a fallback structure with the raw text in short_description.
    """
    # Direct parse attempt
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find the first {...} block in the text (ignores code fences around)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        chunk = m.group(0)
        # Try strict parse first
        try:
            return json.loads(chunk)
        except Exception:
            # Remove trailing commas before closing } or ] and retry
            chunk_nc = re.sub(r",\s*([}\]])", r"\1", chunk)
            try:
                return json.loads(chunk_nc)
            except Exception:
                # Last resort: extract key fields with regex
                try:
                    title_m = re.search(r'"title"\s*:\s*"([^"]*)"', chunk)
                    desc_m = re.search(r'"short_description"\s*:\s*"([^"]*)"', chunk)
                    bullets_m = re.search(r'"bullets"\s*:\s*\[([\s\S]*?)\]', chunk)
                    if not (title_m or desc_m or bullets_m):
                        raise ValueError("no fields matched")
                    result: Dict[str, Any] = {
                        "title": title_m.group(1).strip() if title_m else "",
                        "short_description": desc_m.group(1).strip() if desc_m else "",
                        "bullets": [],
                    }
                    if bullets_m:
                        items = re.findall(r'"([^"]+)"', bullets_m.group(1))
                        result["bullets"] = [s.strip() for s in items if s.strip()]
                    return result
                except Exception:
                    pass

    return {
        "title": "",
        "short_description": text.strip(),
        "bullets": [],
    }


def _split_to_bullets(text: Optional[str]) -> list[str]:
    if not text:
        return []
    # Split by common separators and trim
    parts = re.split(r"[\n;•\-\u2022,]", str(text))
    out = []
    for p in parts:
        p = p.strip().strip("•-— ")
        if p:
            out.append(p)
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq[:10]


def build_product_prompt(
    *,
    product_name: str,
    features: Optional[str] = None,
    audience: Optional[str] = None,
    platform: Optional[str] = None,
    tone: str = "neutral",
    length: str = "medium",
    language: str = "ru",
) -> str:
    parts = []
    profile = get_profile(platform)

    # Build language-specific instruction blocks to improve fidelity
    if language == "ru":
        tone_ru = {
            "selling": "рекламный/убеждающий",
            "concise": "краткий",
            "expert": "экспертный/достоверный",
            "neutral": "нейтральный",
        }
        if platform:
            parts.append(f"Площадка: {platform}")
        parts.append(f"Название товара: {product_name}")
        parts.append(f"Тон: {tone_ru.get(tone, tone)}")
        if audience:
            parts.append(f"Целевая аудитория: {audience}")
        if features:
            parts.append(f"Характеристики: {features}")
        target_desc = min(LENGTH_HINTS.get(length, 300), profile.description_max)
        parts.append("Задача: написать заголовок и краткое описание на русском.")
        parts.append(
            "Строго следуй входным данным, не выдумывай характеристики. "
            "Не упоминай Wi‑Fi/Bluetooth и др., если это явно не указано."
        )
        parts.append(
            "Стиль: естественные русские формулировки без кальки и жаргона; "
            "опиши 1–2 короткими предложениями (16–30 слов каждое); "
            "избегай штампов вроде ‘высококачественный’, ‘лучший’, ‘современный’; "
            "никаких слов ‘пожалуйста’."
        )
        # Platform-specific guidance
        if (platform or "").lower() == "wb":
            parts.append(
                "Стиль WB: без эмодзи и CAPS; никаких обещаний/гарантий; избегай повторов ‘беспроводной’."
            )
            parts.append(
                "Буллеты: 3–5 коротких пунктов по 2–6 слов, без точки на конце."
            )
        elif (platform or "").lower() == "ozon":
            parts.append(
                "Стиль Ozon: нейтральный, информативный; если в названии есть бренд, ставь его ближе к началу заголовка."
            )
            parts.append(
                "Буллеты: 3–6 пунктов по 2–7 слов, без точки на конце."
            )
        else:
            parts.append(
                "Буллеты: 3–6 пунктов по 2–7 слов, без точки на конце; начинай с существительного (пример: ‘Тихие клики’, ‘Стабильная связь 2.4 ГГц’)."
            )
        parts.append(
            "Выводи СТРОГО JSON с полями: title, short_description, bullets (массив строк). Без markdown."
        )
        parts.append(
            f"Ограничения: title ≤ {profile.title_max} символов; short_description ≤ {target_desc} символов; "
            f"bullets {profile.bullets_min}-{profile.bullets_max} пунктов."
        )
    else:
        if platform:
            parts.append(f"Platform: {platform}")
        parts.append(f"Product name: {product_name}")
        parts.append(f"Tone: {TONE_LABELS.get(tone, tone)}")
        if audience:
            parts.append(f"Target audience: {audience}")
        if features:
            parts.append(f"Key features/specs: {features}")
        target_desc = min(LENGTH_HINTS.get(length, 300), profile.description_max)
        parts.append("Task: write a concise, convincing product title and short description.")
        parts.append("Use only provided facts; do not invent specs.")
        parts.append("Output STRICT JSON: title, short_description, bullets (array). No markdown.")
        parts.append(
            f"Constraints: title <= {profile.title_max} chars; short_description <= {target_desc} chars; "
            f"bullets {profile.bullets_min}-{profile.bullets_max} items."
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
    language: str = "ru",
    temperature: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
    progress_cb: Optional[Callable[[float], Awaitable[None]]] = None,
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
        language=language,
    )

    # Cache lookup
    key = _cache_key(
        product_name=product_name,
        features=features,
        platform=platform,
        tone=tone,
        length=length,
        language=language,
    )
    now = asyncio.get_event_loop().time()
    hit = _CACHE.get(key)
    if hit and (now - hit[0]) <= cfg.cache_ttl_sec:
        return dict(hit[1])

    attempt = 0
    last_raw = ""
    payload: Dict[str, Any] = {}
    try:
        while True:
            attempt += 1
            # Choose system prompt per target language
            sys_prompt = SYSTEM_PROMPT_RU if language == "ru" else SYSTEM_PROMPT_EN
            if progress_cb:
                # Stream with approximate progress towards 95%
                profile = get_profile(platform)
                target_desc = min(LENGTH_HINTS.get(length, 300), profile.description_max)
                expected_chars = profile.title_max + target_desc + profile.bullets_max * 25 + 64
                generated = []

                async for chunk in client.generate_stream(
                    prompt,
                    system=sys_prompt,
                    temperature=temperature,
                    max_new_tokens=max_new_tokens,
                    timeout=cfg.llm_timeout,
                ):
                    generated.append(chunk)
                    total = sum(len(c) for c in generated)
                    # Cap at 95% until parsing completes
                    frac = min(0.95, max(0.01, total / max(200, expected_chars)))
                    try:
                        await progress_cb(frac)
                    except Exception:
                        pass
                raw = "".join(generated)
            else:
                raw = await client.generate(
                    prompt,
                    system=sys_prompt,
                    temperature=temperature,
                    max_new_tokens=max_new_tokens,
                    timeout=cfg.llm_timeout,
                )
            last_raw = raw
            payload = _extract_json(raw)
            # Validate structure and ensure title is not empty (fallback produces empty title)
            if (
                isinstance(payload.get("title"), str)
                and payload.get("title", "").strip()
                and isinstance(payload.get("short_description"), str)
                and isinstance(payload.get("bullets"), (list, tuple))
            ):
                break

            if attempt > cfg.gen_max_retries:
                logger.warning(
                    "JSON invalid after %s attempts; returning best-effort parse", attempt
                )
                break

            # Repair attempt: ask the model to fix into JSON
            logger.info("Retrying generation with repair (attempt %s)", attempt)
            repair_prompt = (
                (
                    "Преобразуй текст ниже в СТРОГИЙ JSON с ключами: title, short_description, bullets (массив).\n"
                    "Выведи только JSON, без пояснений.\n\nТекст:\n"
                )
                if language == "ru"
                else (
                    "Convert the text below into STRICT JSON with keys: title, short_description, bullets (array).\n"
                    "Output only the JSON, no comments.\n\nText:\n"
                )
            ) + last_raw
            await asyncio.sleep(cfg.gen_retry_delay_sec)
            rep_sys = REPAIR_SYSTEM_PROMPT_RU if language == "ru" else REPAIR_SYSTEM_PROMPT_EN
            if progress_cb:
                # Repair without streaming; jump progress near completion
                try:
                    await progress_cb(0.96)
                except Exception:
                    pass
                raw = await client.generate(
                    repair_prompt,
                    system=rep_sys,
                    temperature=0.2,
                    max_new_tokens=max_new_tokens,
                    timeout=cfg.llm_timeout,
                )
            else:
                raw = await client.generate(
                    repair_prompt,
                    system=rep_sys,
                    temperature=0.2,
                    max_new_tokens=max_new_tokens,
                    timeout=cfg.llm_timeout,
                )
            payload = _extract_json(raw)
            if (
                isinstance(payload.get("title"), str)
                and isinstance(payload.get("short_description"), str)
                and isinstance(payload.get("bullets"), (list, tuple))
            ):
                break
            await asyncio.sleep(cfg.gen_retry_delay_sec)
    except Exception as e:
        logger.exception("LLM generation failed; falling back to heuristic output: %s", e)
        payload = {}
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
    # Fallbacks for missing fields
    if not title and product_name:
        title = str(product_name)[: profile.title_max].strip()
    if not desc:
        if bullets:
            # Compose a compact sentence from bullets
            desc = "; ".join(bullets)[: profile.description_max].strip()
        elif features:
            # Build bullets from features and also use them to craft a sentence
            feature_bullets = _split_to_bullets(features)
            if not bullets:
                bullets = feature_bullets[: profile.bullets_max]
            desc = ", ".join(feature_bullets)[: profile.description_max].strip()
        elif product_name:
            desc = str(product_name)[: profile.description_max].strip()

    payload.update(title=title, short_description=desc, bullets=bullets)
    if progress_cb:
        try:
            await progress_cb(1.0)
        except Exception:
            pass

    # Store in cache
    _CACHE[key] = (now, dict(payload))
    _CACHE_ORDER.append(key)
    # Enforce cache size
    while len(_CACHE_ORDER) > cfg.cache_size:
        oldest = _CACHE_ORDER.pop(0)
        _CACHE.pop(oldest, None)
    return payload
