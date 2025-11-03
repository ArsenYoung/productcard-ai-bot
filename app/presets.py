from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CategoryPreset:
    code: str
    name_ru: str
    name_en: str
    style_ru: List[str]
    style_en: List[str]


PRESETS: Dict[str, CategoryPreset] = {
    "electronics": CategoryPreset(
        code="electronics",
        name_ru="Электроника",
        name_en="Electronics",
        style_ru=[
            "Избегай общих слов типа ‘высококачественный’; пиши фактами: стандарты, интерфейсы, совместимость.",
            "Не обещай ‘поддерживает всё’; указывай только то, что есть во вводе.",
        ],
        style_en=[
            "Avoid generic adjectives; focus on facts: standards, interfaces, compatibility.",
            "Do not overpromise; only state features provided in the input.",
        ],
    ),
    "apparel": CategoryPreset(
        code="apparel",
        name_ru="Одежда/Обувь",
        name_en="Apparel",
        style_ru=[
            "Упор на материал/посадку/уход; избегай оценочных слов.",
            "Размеры и сезонность упоминай только если есть в вводе.",
        ],
        style_en=[
            "Emphasize material/fit/care; avoid subjective claims.",
            "Mention sizing/seasonality only if provided.",
        ],
    ),
    "home": CategoryPreset(
        code="home",
        name_ru="Дом и кухня",
        name_en="Home & Kitchen",
        style_ru=[
            "Подчеркни практичность и уход; избегай ‘идеально для всего’.",
        ],
        style_en=[
            "Highlight practicality and care; avoid ‘perfect for everything’.",
        ],
    ),
    "beauty": CategoryPreset(
        code="beauty",
        name_ru="Красота и уход",
        name_en="Beauty",
        style_ru=[
            "Без медицинских обещаний; говори о текстуре/аромате/способе применения.",
        ],
        style_en=[
            "No medical claims; talk about texture/scent/application.",
        ],
    ),
    "sports": CategoryPreset(
        code="sports",
        name_ru="Спорт и туризм",
        name_en="Sports & Outdoors",
        style_ru=[
            "Практичность и устойчивость материалов; избегай преувеличений.",
        ],
        style_en=[
            "Practicality and material durability; avoid exaggerations.",
        ],
    ),
}


def list_presets() -> List[CategoryPreset]:
    return list(PRESETS.values())


def get_preset(code: Optional[str]) -> Optional[CategoryPreset]:
    if not code:
        return None
    return PRESETS.get(str(code).lower())

