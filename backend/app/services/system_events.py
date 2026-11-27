"""Muhim hodisalar jurnali (8.3.3): kamera uzilishi, train, servis qayta ishga tushishi, vaqt sakrashi."""

import logging
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.system import SystemEvent

log = logging.getLogger(__name__)
_engine = None


def _sync_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url.replace("+asyncpg", "+psycopg"), pool_pre_ping=True, pool_size=1
        )
    return _engine


def record_sync(
    kind: str, message: str, *, level: str = "info", source: str = "", data: dict[str, Any] | None = None
) -> None:
    try:
        with Session(_sync_engine()) as s:
            s.add(SystemEvent(kind=kind, message=message, level=level, source=source, data=data or {}))
            s.commit()
    except Exception as e:  # jurnal yozilmasa ham ish to'xtamasin
        log.warning("Hodisa jurnaliga yozib bo'lmadi: %s", e)


async def record(
    session, kind: str, message: str, *, level: str = "info", source: str = "", data: dict[str, Any] | None = None
) -> None:
    session.add(SystemEvent(kind=kind, message=message, level=level, source=source, data=data or {}))
    await session.commit()
