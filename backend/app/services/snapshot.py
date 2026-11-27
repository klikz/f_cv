"""Kameraning joriy kadrini olish (API processida, shared memory'dan)."""

import asyncio
import time

import numpy as np
from redis.asyncio import Redis

from app.core import keys
from vision.video.shm import FrameRingReader


async def grab_live_frame(
    redis: Redis, camera_id: int, kind: str, timeout: float = 12.0
) -> tuple[np.ndarray, float] | None:
    """Oqim yopiq bo'lsa iste'molchi sifatida qisqa muddatga ochadi va kadr kutadi."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = await redis.hgetall(keys.stream_status(camera_id, kind))
        if st.get("status") == "online" and st.get("shm"):
            try:
                r = FrameRingReader(st["shm"])
            except (FileNotFoundError, ValueError):
                r = None
            if r is not None:
                try:
                    res = r.read()
                    if res is not None:
                        return res[2], res[1]
                finally:
                    r.close()
        await redis.set(keys.consumer(camera_id, kind, "snapshot"), "1", ex=20)
        await asyncio.sleep(0.4)
    return None
