"""`settings` jadvali: kalit → JSON qiymat (standart qiymatlar bilan)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import Setting

DEFAULTS: dict[str, Any] = {
    # tayyorlik indikatori chegaralari (belgilangan obyektlar soni)
    "dataset.readiness": {"minimal": 50, "ready": 120},
    # avto-yig'ish: {camera_id: {enabled, interval_sec, daily_limit}}
    "dataset.autocollect": {},
    # train standart parametrlari
    "training.defaults": {
        "model_size": "n",
        "epochs": 60,
        "imgsz": 640,
        "batch": 16,
        "negative_ratio": 1.0,
        "patience": 20,
    },
    # vazifa rasmlari umumiy papkasi ("" — data/images); har vazifa: <papka>/cam<id>-<vazifa>
    "storage.images_root": "",
    # telegram
    "telegram.outbox_ttl_hours": 24,
    # disk ogohlantirish chegarasi (% bo'sh)
    "system.disk_warn_free_pct": 10,
    # GPU byudjet
    "inference.max_load": 400,  # inference/s — oshsa fps pasaytiriladi
}


async def get_setting(session: AsyncSession, key: str) -> Any:
    row = await session.get(Setting, key)
    if row is None:
        return DEFAULTS.get(key)
    default = DEFAULTS.get(key)
    if isinstance(default, dict) and isinstance(row.value, dict):
        return {**default, **row.value}
    return row.value


async def set_setting(session: AsyncSession, key: str, value: Any) -> None:
    stmt = (
        insert(Setting)
        .values(key=key, value=value)
        .on_conflict_do_update(index_elements=["key"], set_={"value": value})
    )
    await session.execute(stmt)
    await session.commit()


async def all_settings(session: AsyncSession) -> dict[str, Any]:
    rows = {r.key: r.value for r in (await session.execute(select(Setting))).scalars()}
    return {
        k: (rows.get(k, v) if not isinstance(v, dict) else {**v, **(rows.get(k) or {})}) for k, v in DEFAULTS.items()
    }
