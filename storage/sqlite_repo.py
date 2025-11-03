from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import aiosqlite


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    platform TEXT,
    product_name TEXT,
    features TEXT,
    title TEXT,
    short_description TEXT,
    bullets_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_generations_tg_created
    ON generations(tg_id, created_at DESC);
"""


async def init_db(db_path: str) -> None:
    dir_name = os.path.dirname(db_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()


async def add_generation(
    db_path: str,
    *,
    tg_id: int,
    platform: Optional[str],
    product_name: str,
    features: Optional[str],
    payload: Dict[str, Any],
) -> int:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO generations
            (tg_id, platform, product_name, features, title, short_description, bullets_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tg_id,
                platform,
                product_name,
                features,
                payload.get("title", ""),
                payload.get("short_description", ""),
                json.dumps(payload.get("bullets", []), ensure_ascii=False),
            ),
        )
        await db.commit()
        # fetch last row id
        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        gen_id = int(row[0])
        await cur.close()
        return gen_id


async def recent_generations(
    db_path: str, *, tg_id: int, limit: int
) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, tg_id, platform, product_name, features, title, short_description, bullets_json, created_at
            FROM generations
            WHERE tg_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tg_id, limit),
        )
        rows = await cur.fetchall()
        await cur.close()
        items: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            try:
                item["bullets"] = json.loads(item.pop("bullets_json") or "[]")
            except Exception:
                item["bullets"] = []
            items.append(item)
        return items


async def get_generation(db_path: str, *, gen_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, tg_id, platform, product_name, features, title, short_description, bullets_json, created_at
            FROM generations
            WHERE id = ?
            """,
            (gen_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            return None
        data = dict(row)
        try:
            data["bullets"] = json.loads(data.pop("bullets_json") or "[]")
        except Exception:
            data["bullets"] = []
        return data


async def prune_history(db_path: str, *, tg_id: int, keep: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        # Delete older rows, keeping latest N by created_at
        await db.execute(
            """
            DELETE FROM generations
            WHERE tg_id = ? AND id NOT IN (
                SELECT id FROM generations WHERE tg_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            )
            """,
            (tg_id, tg_id, keep),
        )
        await db.commit()


async def stats_overview(db_path: str) -> Dict[str, Any]:
    """Return simple aggregated stats for admin usage.

    - total_generations: total rows in table
    - users: count of distinct tg_id
    - last_generated_at: most recent created_at (or None)
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT COUNT(*) AS total_generations,
                   COUNT(DISTINCT tg_id) AS users,
                   MAX(created_at) AS last_generated_at
            FROM generations
            """
        )
        row = await cur.fetchone()
        await cur.close()
        return dict(row or {})


async def per_user_counts(db_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return top users by generation count (limited)."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT tg_id, COUNT(*) AS cnt, MIN(created_at) AS first_at, MAX(created_at) AS last_at
            FROM generations
            GROUP BY tg_id
            ORDER BY cnt DESC, last_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]
