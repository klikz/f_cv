"""camera-logic boshqaruvchisi: har faol kamera uchun alohida process; yiqilsa qayta ko'taradi."""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from sqlalchemy import select

from app.core import keys
from app.core.db import get_sessionmaker
from app.core.redis import get_redis
from app.models.cameras import Camera

log = logging.getLogger(__name__)


class Child:
    def __init__(self, camera_id: int) -> None:
        self.camera_id = camera_id
        self.proc: asyncio.subprocess.Process | None = None
        self.restarts = 0
        self.next_start = 0.0

    async def start(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.cli",
            "camera-logic",
            "--camera-id",
            str(self.camera_id),
            stdin=asyncio.subprocess.DEVNULL,
        )
        log.info("camera-logic:%s ishga tushdi (pid %s)", self.camera_id, self.proc.pid)

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def stop(self) -> None:
        if self.alive:
            assert self.proc
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 12)
            except TimeoutError:
                self.proc.kill()
                await self.proc.wait()
            log.info("camera-logic:%s to'xtatildi", self.camera_id)


async def _enabled_ids() -> set[int]:
    async with get_sessionmaker()() as s:
        return set((await s.execute(select(Camera.id).where(Camera.enabled.is_(True)))).scalars().all())


async def record_downtime(redis) -> None:
    """Servis (yoki kompyuter) o'chgan vaqt — oxirgi heartbeat'dan hozirgacha — coverage_gaps ga (sabab: service)."""
    from datetime import UTC, datetime

    from app.core.heartbeat import last_seen
    from app.models.cameras import CoverageGap
    from app.services.system_events import record_sync

    ls = await last_seen(redis, "camera-logic")
    if ls is None:
        return
    gap = time.time() - ls
    if gap < 30:
        return
    async with get_sessionmaker()() as s:
        s.add(
            CoverageGap(
                camera_id=None,
                task_type=None,
                reason="service",
                start_ts=datetime.fromtimestamp(ls, UTC),
                end_ts=datetime.now(UTC),
                detail=f"Servis {int(gap)} s ishlamagan",
            )
        )
        await s.commit()
    await asyncio.to_thread(
        record_sync,
        "service_down",
        f"Kamera logikasi {int(gap // 60)} daq {int(gap % 60)} s ishlamagan (elektr o'chishi yoki qayta ishga tushish)",
        level="warning",
        source="camera-logic",
        data={"seconds": int(gap)},
    )
    log.warning("Servis o'chgan oraliq yozildi: %d s", gap)


async def supervisor_main(stop: asyncio.Event) -> None:
    redis = get_redis()
    await record_downtime(redis)
    children: dict[int, Child] = {}
    reload = asyncio.Event()
    reload.set()

    async def listen() -> None:
        ps = redis.pubsub()
        await ps.subscribe(keys.CH_CAMERAS)
        async for m in ps.listen():
            if m.get("type") == "message":
                reload.set()

    listener = asyncio.create_task(listen())
    wanted: set[int] = set()
    try:
        while not stop.is_set():
            if reload.is_set():
                reload.clear()
                try:
                    wanted = await _enabled_ids()
                except Exception:
                    log.exception("Kameralarni o'qib bo'lmadi")
            now = time.time()
            for cid in list(children):
                if cid not in wanted:
                    await children.pop(cid).stop()
            for cid in wanted:
                ch = children.setdefault(cid, Child(cid))
                if not ch.alive and now >= ch.next_start:
                    if ch.proc is not None:
                        ch.restarts += 1
                        log.warning(
                            "camera-logic:%s yiqilgan (kod %s) — qayta ishga tushirilmoqda", cid, ch.proc.returncode
                        )
                    ch.next_start = now + min(30, 2 ** min(ch.restarts, 5))
                    await ch.start()
                elif ch.alive and now - ch.next_start > 120:
                    ch.restarts = 0
                if ch.alive and now - ch.next_start > 60:
                    hb = await redis.hget(f"fcv:hb:camera-logic:{cid}", "ts")
                    if hb is None or now - float(hb) > 30:
                        log.warning("camera-logic:%s javob bermayapti — qayta ishga tushirilmoqda", cid)
                        await ch.stop()
            try:
                await asyncio.wait_for(stop.wait(), 1.0)
            except TimeoutError:
                pass
    finally:
        listener.cancel()
        await asyncio.gather(*(c.stop() for c in children.values()))
