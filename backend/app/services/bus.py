"""Redis orqali processlararo xabarlar (pub/sub + yo'qolmaydigan hodisalar oqimi)."""

import json
import time
from typing import Any

from redis.asyncio import Redis

from app.core import keys


def _dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


async def publish(redis: Redis, channel: str, data: dict[str, Any]) -> None:
    await redis.publish(channel, _dumps(data))


async def emit_event(redis: Redis, kind: str, data: dict[str, Any], *, durable: bool = False) -> None:
    """UI uchun jonli hodisa; durable=True — Telegram uchun Redis Stream'ga ham yoziladi."""
    payload = {"kind": kind, "ts": time.time(), **data}
    await redis.publish(keys.CH_EVENTS, _dumps(payload))
    if durable:
        await redis.xadd(keys.STREAM_EVENTS, {"data": _dumps(payload)}, maxlen=100_000, approximate=True)


async def camera_changed(redis: Redis, action: str, camera_id: int) -> None:
    await publish(redis, keys.CH_CAMERAS, {"action": action, "camera_id": camera_id})


async def task_changed(redis: Redis, camera_id: int, task_type: str | None = None) -> None:
    await publish(redis, keys.CH_TASKS, {"camera_id": camera_id, "task_type": task_type})
