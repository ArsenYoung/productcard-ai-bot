from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PlatformProfile:
    code: str
    name: str
    title_max: int
    description_max: int
    bullets_min: int
    bullets_max: int


PROFILES: Dict[str, PlatformProfile] = {
    # Common marketplace friendly defaults; can be tuned
    "ozon": PlatformProfile(
        code="ozon", name="Ozon", title_max=70, description_max=300, bullets_min=3, bullets_max=6
    ),
    "wb": PlatformProfile(
        code="wb", name="Wildberries", title_max=70, description_max=300, bullets_min=3, bullets_max=6
    ),
    "etsy": PlatformProfile(
        code="etsy", name="Etsy", title_max=130, description_max=1000, bullets_min=3, bullets_max=10
    ),
    "shopify": PlatformProfile(
        code="shopify", name="Shopify", title_max=80, description_max=500, bullets_min=3, bullets_max=8
    ),
}


def get_profile(code: str | None) -> PlatformProfile:
    if not code:
        return PROFILES["ozon"]
    return PROFILES.get(code, PROFILES["ozon"])


# Tone presets and length presets for prompting
TONE_LABELS = {
    "selling": "selling/persuasive",
    "concise": "concise",
    "expert": "expert/credible",
    "neutral": "neutral",
}

LENGTH_HINTS = {
    # Target description lengths; will be capped by profile.description_max
    "short": 150,
    "medium": 300,
    "long": 500,
}

