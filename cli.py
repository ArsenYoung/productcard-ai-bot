import argparse
import asyncio
import json
from typing import Optional

from services.generation_service import generate_product_card


async def _run(
    *,
    name: str,
    features: Optional[str],
    platform: Optional[str],
    tone: str,
    audience: Optional[str],
    language: str,
):
    payload = await generate_product_card(
        product_name=name,
        features=features,
        platform=platform,
        tone=tone,
        audience=audience,
        language=language,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(
        description="Generate a product card JSON using a local Ollama model (phi3:mini by default).",
    )
    p.add_argument("name", help="Product name")
    p.add_argument(
        "-f",
        "--features",
        help="Product features/specs (free text)",
    )
    p.add_argument("--platform", help="Target platform (e.g., ozon, wb, etsy, shopify)")
    p.add_argument("--tone", default="neutral", help="Writing tone (default: neutral)")
    p.add_argument("--audience", help="Target audience")
    p.add_argument("--lang", default="ru", choices=["ru", "en"], help="Output language: ru or en (default: ru)")

    args = p.parse_args()
    asyncio.run(
        _run(
            name=args.name,
            features=args.features,
            platform=args.platform,
            tone=args.tone,
            audience=args.audience,
            language=args.lang,
        )
    )


if __name__ == "__main__":
    main()
