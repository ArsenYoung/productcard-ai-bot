import asyncio

import pytest

from storage.sqlite_repo import init_db, add_generation, get_generation, recent_generations, prune_history


@pytest.mark.asyncio
async def test_sqlite_repo_crud(tmp_path):
    db = tmp_path / "test.db"
    await init_db(str(db))

    gen_id = await add_generation(
        str(db),
        tg_id=123,
        platform="ozon",
        product_name="Mouse",
        features="2.4G",
        payload={
            "title": "Wireless Mouse",
            "short_description": "Compact wireless mouse",
            "bullets": ["Silent"],
        },
    )

    row = await get_generation(str(db), gen_id=gen_id)
    assert row and row["title"] == "Wireless Mouse"

    # Insert more and test recent + prune
    for i in range(6):
        await add_generation(
            str(db),
            tg_id=123,
            platform="ozon",
            product_name=f"Item{i}",
            features=None,
            payload={"title": str(i), "short_description": "x", "bullets": []},
        )

    await prune_history(str(db), tg_id=123, keep=3)
    items = await recent_generations(str(db), tg_id=123, limit=10)
    assert len(items) <= 3

