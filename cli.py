import argparse
import asyncio
import json
import logging
import sys
from typing import Optional

from services.generation_service import generate_product_card


logger = logging.getLogger("productcard.cli")


async def _run(
    *,
    name: str,
    features: Optional[str],
    platform: Optional[str],
    tone: str,
    audience: Optional[str],
    language: str,
    category: Optional[str],
):
    payload = await generate_product_card(
        product_name=name,
        features=features,
        platform=platform,
        tone=tone,
        audience=audience,
        language=language,
        category=category,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
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
    p.add_argument("--category", help="Optional category preset (e.g., electronics, apparel, home, beauty, sports)")

    args = p.parse_args()
    try:
        asyncio.run(
            _run(
                name=args.name,
                features=args.features,
                platform=args.platform,
                tone=args.tone,
                audience=args.audience,
                language=args.lang,
                category=args.category,
            )
        )
    except Exception as exc:
        logger.exception("Generation failed")
        print(f"Generation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
