"""Fon processlari uchun umumiy ishga tushiruvchi: loglash, heartbeat, to'g'ri to'xtash."""

import asyncio
import contextlib
import logging
import signal
from collections.abc import Awaitable, Callable

from app.core.config import get_settings
from app.core.heartbeat import heartbeat_loop
from app.core.logging import setup_logging
from app.core.redis import close_redis, get_redis

log = logging.getLogger(__name__)

MainFn = Callable[[asyncio.Event], Awaitable[None]]


async def _run(name: str, main: MainFn) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    redis = get_redis()
    hb = asyncio.create_task(heartbeat_loop(redis, name), name=f"{name}-heartbeat")
    log.info("Ishga tushdi")
    if not name.startswith("camera-logic:"):
        from app.services.system_events import record_sync

        await asyncio.to_thread(record_sync, "service_start", f"{name} ishga tushdi", source=name)
    try:
        await main(stop)
    finally:
        hb.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb
        with contextlib.suppress(Exception):
            await redis.delete(f"fcv:hb:{name}")
        await close_redis()
        log.info("To'xtadi")


def run_process(name: str, main: MainFn) -> None:
    settings = get_settings()
    settings.ensure_data_dirs()
    setup_logging(name)
    asyncio.run(_run(name, main))


async def idle_loop(stop: asyncio.Event) -> None:
    """Hozircha bo'sh sikl — keyingi bosqichlarda haqiqiy ish bilan almashtiriladi."""
    await stop.wait()
