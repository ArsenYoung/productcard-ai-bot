import asyncio
import json

import pytest

import services.generation_service as gen


class StubClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    async def generate(self, *args, **kwargs):
        await asyncio.sleep(0)
        return self.outputs.pop(0)


@pytest.mark.asyncio
async def test_generation_repair_and_enforce(monkeypatch):
    # First call returns non-JSON, second returns JSON with long title and too many bullets
    bad = "Not a JSON at all"
    good_payload = {
        "title": "T" * 200,
        "short_description": "D" * 1000,
        "bullets": [str(i) for i in range(20)],
    }
    good = json.dumps(good_payload)

    stub = StubClient([bad, good])
    monkeypatch.setattr(gen, "OllamaClient", lambda base_url, model: stub)

    # Speed up retries in tests
    monkeypatch.setattr(gen, "get_settings", lambda: type("S", (), {
        "llm_base_url": "http://x", "llm_model": "phi3:mini",
        "llm_temperature": 0.6, "llm_max_new_tokens": 100,
        "llm_timeout": 5.0, "gen_max_retries": 2, "gen_retry_delay_sec": 0.0
    })())

    payload = await gen.generate_product_card(
        product_name="A",
        features=None,
        platform="ozon",
        tone="neutral",
        length="short",
    )

    # Enforced by ozon profile: title <= 70, desc <= 300, bullets <= 6
    assert len(payload["title"]) <= 70
    assert len(payload["short_description"]) <= 300
    assert len(payload["bullets"]) <= 6

