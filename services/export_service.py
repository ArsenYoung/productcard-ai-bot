from __future__ import annotations

import csv
import io
from typing import Dict, Any, List


def _bullets_to_lines(bullets: Any) -> List[str]:
    if isinstance(bullets, list):
        return [str(x) for x in bullets if str(x).strip()]
    try:
        # fallback if bullets serialized as string
        return [s.strip() for s in str(bullets).split(";") if s.strip()]
    except Exception:
        return []


def render_text_export(gen: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"Platform: {gen.get('platform','')}")
    lines.append(f"Input: {gen.get('product_name','')}")
    feats = gen.get("features")
    if feats:
        lines.append(f"Features: {feats}")
    lines.append("")
    lines.append(f"Title: {gen.get('title','')}")
    lines.append("")
    lines.append("Description:")
    lines.append(str(gen.get("short_description", "")))
    lines.append("")
    bl = _bullets_to_lines(gen.get("bullets"))
    if bl:
        lines.append("Bullets:")
        lines += [f"- {b}" for b in bl]
    return "\n".join(lines).strip() + "\n"


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

