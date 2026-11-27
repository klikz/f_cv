"""Process heartbeat'i Redis'da: `fcv:hb:<nom>` hash (nom, pid, vaqt), TTL bilan.

TTL tugasa kalit o'chadi → process "javob bermayapti" deb ko'rinadi.
"""

import asyncio
import logging
import os
import socket
import time
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings

log = logging.getLogger(__name__)

HB_PREFIX = "fcv:hb:"
LASTSEEN_PREFIX = "fcv:lastseen:"

# /api/health shu processlarni kutadi (camera-logic kamera bo'yicha alohida, ixtiyoriy)
EXPECTED_PROCESSES = ("api", "video-service", "inference-server", "trainer", "telegram-service")


async def write_heartbeat(redis: Redis, name: str, extra: dict[str, Any] | None = None) -> None:
    s = get_settings()
    data = {"name": name, "pid": os.getpid(), "host": socket.gethostname(), "ts": time.time()}
    if extra:
        data.update({k: str(v) for k, v in extra.items()})
    key = HB_PREFIX + name
    async with redis.pipeline(transaction=True) as p:
        p.hset(key, mapping=data)
        p.expire(key, s.heartbeat_ttl_sec)
        p.set(LASTSEEN_PREFIX + name, data["ts"])  # TTL siz — o'chgan oraliqni aniqlash uchun (8.1.5)
        await p.execute()


async def heartbeat_loop(redis: Redis, name: str) -> None:
    """Fon vazifasi: Redis vaqtincha yo'q bo'lsa ham to'xtamaydi."""
    from app.core.sdnotify import notify

    interval = get_settings().heartbeat_interval_sec
    warned = False
    notify("READY=1")
    wall0, mono0 = time.time(), time.monotonic()
    while True:
        # server vaqti keskin sakradimi (8.1.8)
        wall, mono = time.time(), time.monotonic()
        jump = (wall - wall0) - (mono - mono0)
        if abs(jump) > 30:
            log.warning("Server vaqti keskin o'zgardi: %+.0f s", jump)
            if name == "api":
                from app.services.system_events import record_sync

                await asyncio.to_thread(
                    record_sync,
                    "time_jump",
                    f"Server vaqti {jump:+.0f} s ga o'zgardi",
                    level="warning",
                    source=name,
                    data={"jump_sec": round(jump)},
                )
        wall0, mono0 = wall, mono
        try:
            await write_heartbeat(redis, name)
            notify("WATCHDOG=1")
            if warned:
                log.info("Redis bilan aloqa tiklandi")
                warned = False
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if not warned:
                log.warning("Heartbeat yozib bo'lmadi: %s", e)
                warned = True
        await asyncio.sleep(interval)


async def last_seen(redis: Redis, name: str) -> float | None:
    v = await redis.get(LASTSEEN_PREFIX + name)
    return float(v) if v else None


async def read_heartbeats(redis: Redis) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    async for key in redis.scan_iter(match=HB_PREFIX + "*", count=200):
        data = await redis.hgetall(key)
        if data:
            name = key.removeprefix(HB_PREFIX)
            result[name] = {
                "name": name,
                "pid": int(data.get("pid", 0)),
                "host": data.get("host"),
                "ts": float(data.get("ts", 0)),
            }
    return result
