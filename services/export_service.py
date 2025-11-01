from __future__ import annotations

import csv
import io
from typing import Dict, Any, List, Optional
import html as _html
import json
import re


def _bullets_to_lines(bullets: Any) -> List[str]:
    if isinstance(bullets, list):
        return [str(x) for x in bullets if str(x).strip()]
    try:
        # fallback if bullets serialized as string
        return [s.strip() for s in str(bullets).split(";") if s.strip()]
    except Exception:
        return []


def _try_parse_json_like_blob(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse a JSON object even if wrapped in code fences or with trailing commas.

    Returns dict on success, or None.
    """
    if not text or not isinstance(text, str):
        return None

    # Remove code fences like ```json ... ```
    cleaned = re.sub(r"^```\w*\n|```$", "", text.strip(), flags=re.MULTILINE)

    # Try direct load
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Extract the first {...} block
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if not m:
        return None
    chunk = m.group(0)

    # Remove trailing commas before } or ]
    chunk_nc = re.sub(r",\s*([}\]])", r"\1", chunk)
    try:
        return json.loads(chunk_nc)
    except Exception:
        pass

    # Last resort: permissive regex extraction for common fields
    try:
        title_m = re.search(r'"title"\s*:\s*"([^"]*)"', chunk)
        desc_m = re.search(r'"short_description"\s*:\s*"([^"]*)"', chunk)
        bullets_m = re.search(r'"bullets"\s*:\s*\[([\s\S]*?)\]', chunk)
        if not (title_m or desc_m or bullets_m):
            return None
        result: Dict[str, Any] = {
            "title": title_m.group(1).strip() if title_m else "",
            "short_description": desc_m.group(1).strip() if desc_m else "",
            "bullets": [],
        }
        if bullets_m:
            # Extract all string items inside the array
            items = re.findall(r'"([^"]+)"', bullets_m.group(1))
            result["bullets"] = [s.strip() for s in items if s.strip()]
        return result
    except Exception:
        return None


def render_text_export(gen: Dict[str, Any], lang: str = "en") -> str:
    """Render plain-text card for Telegram.

    - Localized labels (ru/en)
    - Attempts to recover from accidental JSON blob in description
    """
    # Attempt to recover if description accidentally contains a JSON blob
    desc_raw = str(gen.get("short_description", ""))
    maybe = _try_parse_json_like_blob(desc_raw)
    if isinstance(maybe, dict) and set(["title", "short_description", "bullets"]).issubset(maybe.keys()):
        # Replace fields only if parsed values are meaningful; otherwise keep originals
        gen = dict(gen)
        parsed_title = str(maybe.get("title", "")).strip()
        parsed_desc = str(maybe.get("short_description", "")).strip()
        parsed_bullets = maybe.get("bullets") if isinstance(maybe.get("bullets"), list) else None

        if parsed_title:
            gen["title"] = parsed_title
        if parsed_desc:
            gen["short_description"] = parsed_desc
        if parsed_bullets and any(str(x).strip() for x in parsed_bullets):
            gen["bullets"] = parsed_bullets

    # Labels
    lang = (lang or "en").lower()
    if lang == "ru":
        L = {
            "platform": "Площадка",
            "input": "Ввод",
            "features": "Характеристики",
            "title": "Заголовок",
            "description": "Описание",
            "bullets": "Пункты",
        }
    else:
        L = {
            "platform": "Platform",
            "input": "Input",
            "features": "Features",
            "title": "Title",
            "description": "Description",
            "bullets": "Bullets",
        }

    lines = []
    lines.append(f"{L['platform']}: {gen.get('platform','')}")
    lines.append(f"{L['input']}: {gen.get('product_name','')}")
    feats = gen.get("features")
    if feats:
        lines.append(f"{L['features']}: {feats}")
    lines.append("")
    lines.append(f"{L['title']}: {gen.get('title','')}")
    lines.append("")
    lines.append(f"{L['description']}:")
    lines.append(str(gen.get("short_description", "")))
    lines.append("")
    bl = _bullets_to_lines(gen.get("bullets"))
    if bl:
        lines.append(f"{L['bullets']}:")
        lines += [f"- {b}" for b in bl]
    return "\n".join(lines).strip() + "\n"


def render_telegram_message(gen: Dict[str, Any], lang: str = "en") -> str:
    """Render a pretty, human-friendly Telegram message in HTML.

    Includes all important fields with clear sectioning and bullet points.
    Safe for ParseMode.HTML (escapes user/model text).
    """
    def esc(v: Any) -> str:
        return _html.escape(str(v or "").strip())

    # Attempt recovery from JSON blob
    maybe = _try_parse_json_like_blob(str(gen.get("short_description", "")))
    if isinstance(maybe, dict) and {"title", "short_description", "bullets"}.issubset(maybe.keys()):
        gen = dict(gen)
        parsed_title = str(maybe.get("title", "")).strip()
        parsed_desc = str(maybe.get("short_description", "")).strip()
        parsed_bullets = maybe.get("bullets") if isinstance(maybe.get("bullets"), list) else None
        if parsed_title:
            gen["title"] = parsed_title
        if parsed_desc:
            gen["short_description"] = parsed_desc
        if parsed_bullets and any(str(x).strip() for x in parsed_bullets):
            gen["bullets"] = parsed_bullets

    title = esc(gen.get("title", ""))
    desc = esc(gen.get("short_description", ""))
    platform = esc(gen.get("platform", ""))
    pname = esc(gen.get("product_name", ""))
    feats = esc(gen.get("features", ""))
    bullets = _bullets_to_lines(gen.get("bullets"))

    # Localized labels
    lang = (lang or "en").lower()
    if lang == "ru":
        lbl_features = "Ключевые преимущества"
        lbl_details = "Детали"
        lbl_platform = "Площадка"
        lbl_input = "Ввод"
        lbl_attrs = "Характеристики"
    else:
        lbl_features = "Key Features"
        lbl_details = "Details"
        lbl_platform = "Platform"
        lbl_input = "Input"
        lbl_attrs = "Attributes"

    lines: List[str] = []
    if title:
        lines.append(f"<b>🛍️ {title}</b>")
    if desc:
        lines.append(desc)

    if bullets:
        lines.append(f"<b>{lbl_features}</b>")
        # Use • as a simple bullet that renders well in Telegram
        for b in bullets:
            lines.append(f"• {esc(b)}")

    meta: List[str] = []
    if platform:
        meta.append(f"{lbl_platform}: <code>{platform}</code>")
    if pname:
        meta.append(f"{lbl_input}: {pname}")
    if feats:
        meta.append(f"{lbl_attrs}: {feats}")
    if meta:
        lines.append("")
        lines.append(f"<b>{lbl_details}</b>")
        lines.extend(meta)

    return "\n".join([ln for ln in lines if str(ln).strip()])


def render_csv_export(gen: Dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "platform",
            "product_name",
            "features",
            "title",
            "short_description",
            "bullets_joined",
        ]
    )
    bullets = " | ".join(_bullets_to_lines(gen.get("bullets")))
    writer.writerow(
        [
            gen.get("platform", ""),
            gen.get("product_name", ""),
            gen.get("features", ""),
            gen.get("title", ""),
            gen.get("short_description", ""),
            bullets,
        ]
    )
    return output.getvalue()
