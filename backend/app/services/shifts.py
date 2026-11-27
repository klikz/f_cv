"""Smenani aniqlash: vaqt → (smena, smena sanasi).

Qoidalar (PLAN.md 1.11):
- smenalar to'plami `effective_from` bo'yicha versiyalanadi; hodisa vaqtida amalda bo'lgan to'plam olinadi;
- yarim tundan o'tuvchi smena **boshlangan sanaga** tegishli;
- hech bir smenaga tushmasa — "smenadan tashqari" (None).
- vaqt hisobi mahalliy (Asia/Tashkent) vaqtda; kirish UTC/aware datetime.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings


@dataclass(frozen=True, slots=True)
class ShiftDef:
    id: int
    name: str
    start_time: time
    end_time: time
    effective_from: datetime


@dataclass(frozen=True, slots=True)
class ShiftMatch:
    shift_id: int
    shift_name: str
    shift_date: date


DEFAULT_SHIFTS: tuple[tuple[str, time, time], ...] = (
    ("Kunduzgi smena", time(8, 0), time(19, 0)),
    ("Tungi smena", time(19, 0), time(8, 0)),
)


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def active_set(shifts: Sequence[ShiftDef], ts: datetime) -> list[ShiftDef]:
    """`ts` paytida amalda bo'lgan smenalar to'plami."""
    if ts.tzinfo is None:
        raise ValueError("ts timezone-aware bo'lishi kerak")
    candidates = [s.effective_from for s in shifts if s.effective_from <= ts]
    if not candidates:
        return []
    eff = max(candidates)
    return [s for s in shifts if s.effective_from == eff]


def match_shift(shifts: Sequence[ShiftDef], ts: datetime, tz: ZoneInfo | None = None) -> ShiftMatch | None:
    """Vaqt → smena va smena sanasi. Smenadan tashqari bo'lsa None."""
    tz = tz or _tz()
    local = ts.astimezone(tz)
    t = local.time().replace(tzinfo=None)
    d = local.date()
    for s in active_set(shifts, ts):
        if s.start_time < s.end_time:
            if s.start_time <= t < s.end_time:
                return ShiftMatch(s.id, s.name, d)
        else:  # yarim tundan o'tadi (yoki 24 soatlik: start == end)
            if t >= s.start_time:
                return ShiftMatch(s.id, s.name, d)
            if t < s.end_time:
                return ShiftMatch(s.id, s.name, d - timedelta(days=1))
    return None


class ShiftResolver:
    """DB dagi smenalarni keshlab, hodisa vaqtida smenani aniqlaydi."""

    def __init__(self, cache_ttl_sec: float = 60.0) -> None:
        self._shifts: list[ShiftDef] = []
        self._loaded_at: datetime | None = None
        self._ttl = timedelta(seconds=cache_ttl_sec)

    async def load(self, session: AsyncSession) -> None:
        from app.models.shifts import Shift

        rows = (await session.execute(select(Shift).order_by(Shift.effective_from, Shift.position))).scalars()
        self._shifts = [ShiftDef(r.id, r.name, r.start_time, r.end_time, r.effective_from) for r in rows]
        self._loaded_at = datetime.now().astimezone()

    def invalidate(self) -> None:
        self._loaded_at = None

    async def resolve(self, session: AsyncSession, ts: datetime) -> ShiftMatch | None:
        now = datetime.now().astimezone()
        if self._loaded_at is None or now - self._loaded_at > self._ttl:
            await self.load(session)
        return match_shift(self._shifts, ts)
