"""Smenalar: joriy jadval, yangi jadval (`effective_from` bilan — faqat kelajakka ta'sir qiladi), tarix."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep
from app.core.config import get_settings
from app.models.shifts import Shift
from app.services import bus
from app.services.shifts import ShiftDef, active_set, match_shift

router = APIRouter(prefix="/shifts", tags=["shifts"])


class ShiftIO(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=100)
    start_time: time
    end_time: time


class ShiftSetIn(BaseModel):
    shifts: list[ShiftIO] = Field(min_length=1, max_length=6)
    effective_from: datetime | None = None  # bo'sh — hozirdan


def _minutes(s: ShiftIO) -> list[tuple[int, int]]:
    a = s.start_time.hour * 60 + s.start_time.minute
    b = s.end_time.hour * 60 + s.end_time.minute
    if a < b:
        return [(a, b)]
    return [(a, 1440), (0, b)] if b > 0 else [(a, 1440)]


def validate(shifts: list[ShiftIO]) -> list[str]:
    """Ustma-ust tushish — xato; bo'shliq — ogohlantirish (hodisalar "smenadan tashqari" bo'ladi)."""
    cover = [0] * 1440
    for s in shifts:
        if s.start_time == s.end_time and len(shifts) > 1:
            raise HTTPException(422, f"'{s.name}': boshlanish va tugash bir xil")
        for a, b in _minutes(s):
            for m in range(a, b):
                cover[m] += 1
    if any(c > 1 for c in cover):
        raise HTTPException(422, "Smenalar ustma-ust tushmoqda — vaqtlarni tekshiring")
    gaps = sum(1 for c in cover if c == 0)
    return (
        [f"Smenalar orasida {gaps} daqiqa bo'shliq bor — bu vaqtdagi hodisalar 'smenadan tashqari' deb belgilanadi"]
        if gaps
        else []
    )


def _defs(rows) -> list[ShiftDef]:
    return [ShiftDef(r.id, r.name, r.start_time, r.end_time, r.effective_from) for r in rows]


@router.get("")
async def get_shifts(session: SessionDep) -> dict:
    rows = (await session.execute(select(Shift).order_by(Shift.effective_from, Shift.position))).scalars().all()
    defs = _defs(rows)
    now = datetime.now(UTC)
    cur = active_set(defs, now)
    future = sorted({d.effective_from for d in defs if d.effective_from > now})
    history = sorted({d.effective_from for d in defs}, reverse=True)
    m = match_shift(defs, now)
    return {
        "current": [
            {
                "id": d.id,
                "name": d.name,
                "start_time": d.start_time.isoformat("minutes"),
                "end_time": d.end_time.isoformat("minutes"),
            }
            for d in cur
        ],
        "effective_from": cur[0].effective_from if cur else None,
        "now": {"shift_id": m.shift_id, "shift_name": m.shift_name, "shift_date": m.shift_date} if m else None,
        "scheduled": [
            {
                "effective_from": f,
                "shifts": [
                    {
                        "name": d.name,
                        "start_time": d.start_time.isoformat("minutes"),
                        "end_time": d.end_time.isoformat("minutes"),
                    }
                    for d in defs
                    if d.effective_from == f
                ],
            }
            for f in future
        ],
        "history": [
            {
                "effective_from": f,
                "shifts": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "start_time": d.start_time.isoformat("minutes"),
                        "end_time": d.end_time.isoformat("minutes"),
                    }
                    for d in defs
                    if d.effective_from == f
                ],
            }
            for f in history
        ],
    }


@router.post("/validate")
async def validate_set(data: ShiftSetIn) -> dict:
    return {"warnings": validate(data.shifts)}


@router.post("")
async def new_set(data: ShiftSetIn, session: SessionDep, redis: RedisDep) -> dict:
    warnings = validate(data.shifts)
    eff = data.effective_from or datetime.now(UTC)
    if eff.tzinfo is None:
        eff = eff.replace(tzinfo=ZoneInfo(get_settings().timezone))
    if eff < datetime.now(UTC) - timedelta(minutes=1):
        raise HTTPException(422, "O'zgarish faqat kelajakka ta'sir qiladi — o'tgan vaqtni tanlab bo'lmaydi")
    for i, s in enumerate(data.shifts):
        session.add(
            Shift(name=s.name.strip(), start_time=s.start_time, end_time=s.end_time, effective_from=eff, position=i)
        )
    await session.commit()
    await bus.publish(redis, "fcv:ch:shifts", {"effective_from": eff.isoformat()})
    return {"effective_from": eff, "warnings": warnings}
