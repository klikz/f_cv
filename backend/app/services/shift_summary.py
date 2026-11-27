"""Bitta kamera uchun smena davomidagi umumiy ko'rsatkichlar (Telegram "Smena hisoboti" uchun).

Hisob qoidalari hisobotlar sahifasi bilan bir xil: bekor qilinganlar hisobga olinmaydi, teskari yo'nalish
kamera siyosatiga ko'ra ayiriladi yoki tashlab yuboriladi.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cameras import CoverageGap
from app.models.catalog import Product
from app.models.counting import CountEvent
from app.models.equipment import CycleEvent, EquipmentInterval
from app.models.tasks import CameraTask, CountingConfig


def count_sign(direction: str, cfg: CountingConfig | None) -> int:
    """Sanoq hodisasining asosiy hisobdagi ulushi: +1, -1 (ayiriladi) yoki 0 (hisobga kirmaydi)."""
    if direction != "reverse" or cfg is None or cfg.direction == "both":
        return 1
    return -1 if cfg.reverse_policy == "subtract" else 0


async def camera_shift_summary(
    session: AsyncSession,
    camera_id: int,
    shift_id: int,
    shift_date: date,
    start: datetime,
    end: datetime,
    recent_from: datetime | None = None,
) -> dict:
    """[start, end) oralig'idagi ko'rsatkichlar. `recent_from` — "oxirgi N daqiqa" sanog'i uchun."""
    tasks = set(
        (
            await session.execute(
                select(CameraTask.task_type).where(CameraTask.camera_id == camera_id, CameraTask.enabled.is_(True))
            )
        ).scalars()
    )
    out: dict = {"tasks": sorted(tasks)}

    # --- sanoq ---
    cfg = await session.get(CountingConfig, camera_id)
    rows = (
        await session.execute(
            select(CountEvent.product_id, CountEvent.status, CountEvent.direction, CountEvent.ts).where(
                CountEvent.camera_id == camera_id,
                CountEvent.shift_date == shift_date,
                CountEvent.shift_id == shift_id,
                CountEvent.status != "cancelled",
            )
        )
    ).all()
    if rows or "counting" in tasks:
        names = dict((await session.execute(select(Product.id, Product.name))).all())
        total = uncertain = recent = 0
        by_prod: dict[int | None, int] = defaultdict(int)
        for pid, status, direction, ts in rows:
            sign = count_sign(direction, cfg)
            if not sign:
                continue
            total += sign
            by_prod[pid] += sign
            uncertain += int(status == "uncertain")
            if recent_from and ts >= recent_from:
                recent += sign
        out["counting"] = {
            "total": total,
            "uncertain": uncertain,
            "recent": recent if recent_from else None,
            "by_product": sorted(
                ({"name": names.get(pid or 0, "Noaniq"), "count": c} for pid, c in by_prod.items() if c),
                key=lambda x: -x["count"],
            ),
        }

    # --- uskuna ---
    ivs = (
        (
            await session.execute(
                select(EquipmentInterval).where(
                    EquipmentInterval.camera_id == camera_id,
                    EquipmentInterval.start_ts < end,
                    EquipmentInterval.end_ts.is_(None) | (EquipmentInterval.end_ts > start),
                )
            )
        )
        .scalars()
        .all()
    )
    if ivs or "equipment" in tasks:
        sec = {"running": 0.0, "stopped": 0.0, "unknown": 0.0}
        stops = 0
        for iv in ivs:
            d = max(0.0, (min(iv.end_ts or end, end) - max(iv.start_ts, start)).total_seconds())
            st = iv.state if iv.state in ("running", "stopped") else "unknown"
            sec[st] += d
            stops += int(st == "stopped" and iv.start_ts >= start)
        cycles = (
            await session.execute(
                select(CycleEvent.duration, CycleEvent.is_micro_stop).where(
                    CycleEvent.camera_id == camera_id, CycleEvent.end_ts >= start, CycleEvent.end_ts < end
                )
            )
        ).all()
        known = sec["running"] + sec["stopped"]
        out["equipment"] = {
            **sec,
            "stops": stops,
            "utilization_pct": round(sec["running"] / known * 100, 1) if known else None,
            "cycles": len(cycles),
            "avg_cycle_sec": round(sum(c[0] for c in cycles) / len(cycles), 1) if cycles else None,
            "micro_stops": sum(int(c[1]) for c in cycles),
        }

    # --- sanalmagan vaqt (kamera uzilgan, train, servis) ---
    gaps = (
        await session.execute(
            select(CoverageGap.start_ts, CoverageGap.end_ts).where(
                CoverageGap.camera_id.is_(None) | (CoverageGap.camera_id == camera_id),
                CoverageGap.start_ts < end,
                CoverageGap.end_ts.is_(None) | (CoverageGap.end_ts > start),
            )
        )
    ).all()
    out["gap_sec"] = sum(max(0.0, (min(e or end, end) - max(s, start)).total_seconds()) for s, e in gaps)
    return out
