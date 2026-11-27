"""WebSocket: JPEG + metadata (ikkilik), holat va hodisalar (JSON).

- `/api/ws/grid`        — mijoz `{"cameras": [1,2,3], "ai": true}` yuboradi; grid profili (sub).
- `/api/ws/camera/{id}` — `?profile=main|analysis` — kamera sahifasi / sozlash sahifalari.
- `/api/ws/events`      — faqat jonli hodisalar (sanoq, uskuna, train, telegram).

Har API processida bitta Redis tinglovchi (`fcv:ch:frames:*` + holat/hodisa kanallari).
Sekin mijoz: har (kamera, profil) uchun faqat **oxirgi** kadr saqlanadi — navbat to'lmaydi.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core import keys
from app.core.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter()

VIEWER_TTL = 15


@dataclass(eq=False)
class Client:
    ws: WebSocket
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    subs: set[tuple[int, str]] = field(default_factory=set)
    ai: bool = False
    events: bool = True
    latest: dict[tuple[int, str], bytes] = field(default_factory=dict)
    json_q: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=200))
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    sent_frames: int = 0
    dropped_frames: int = 0


class Hub:
    def __init__(self) -> None:
        self.clients: set[Client] = set()
        self._task: asyncio.Task | None = None
        self._redis_bin: Redis | None = None

    def ensure_started(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._listen(), name="ws-hub")

    async def _listen(self) -> None:
        while True:
            try:
                self._redis_bin = Redis.from_url(get_settings().redis_url, decode_responses=False)
                ps = self._redis_bin.pubsub()
                await ps.psubscribe(keys.CH_FRAMES_PATTERN)
                await ps.subscribe(keys.CH_STREAM_STATUS, keys.CH_EVENTS)
                async for m in ps.listen():
                    t = m.get("type")
                    if t == "pmessage":
                        self._on_frame(m["channel"].decode(), m["data"])
                    elif t == "message":
                        ch = m["channel"].decode()
                        kind = "stream_status" if ch == keys.CH_STREAM_STATUS else "event"
                        self._broadcast_json(kind, m["data"].decode())
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("WS hub: Redis tinglovchi uzildi (%s), qayta ulanish...", e)
                await asyncio.sleep(1)

    def _on_frame(self, channel: str, data: bytes) -> None:
        # fcv:ch:frames:<cam>:<profile>
        parts = channel.split(":")
        try:
            key = (int(parts[3]), parts[4])
        except (IndexError, ValueError):
            return
        for c in self.clients:
            if key in c.subs:
                if key in c.latest:
                    c.dropped_frames += 1
                c.latest[key] = data
                c.wake.set()

    def _broadcast_json(self, kind: str, raw: str) -> None:
        msg = json.dumps({"type": kind, "data": json.loads(raw)}, ensure_ascii=False)
        for c in self.clients:
            if kind == "event" and not c.events:
                continue
            try:
                c.json_q.put_nowait(msg)
                c.wake.set()
            except asyncio.QueueFull:
                pass


hub = Hub()


async def _sender(c: Client) -> None:
    while True:
        await c.wake.wait()
        c.wake.clear()
        while not c.json_q.empty():
            await c.ws.send_text(c.json_q.get_nowait())
        frames, c.latest = c.latest, {}
        for data in frames.values():
            await c.ws.send_bytes(data)
            c.sent_frames += 1


async def _keepalive(c: Client, redis: Redis) -> None:
    """Tomoshabin kalitlarini yangilash + har soniyada holat (sanoq, uskuna, oqimlar)."""
    last_viewers = 0.0
    while True:
        now = time.time()
        if now - last_viewers > 5:
            last_viewers = now
            async with redis.pipeline(transaction=False) as p:
                for cam, prof in c.subs:
                    p.set(keys.viewer(cam, prof, c.id), "1", ex=VIEWER_TTL)
                    if prof == "main":
                        p.set(keys.consumer(cam, "main", f"ws-{c.id}"), "1", ex=VIEWER_TTL)
                    if prof == "grid" and c.ai:
                        p.set(keys.ai_vision(cam), "1", ex=VIEWER_TTL)
                await p.execute()
        cams = sorted({cam for cam, _ in c.subs})
        if cams:
            async with redis.pipeline(transaction=False) as p:
                for cam in cams:
                    p.get(keys.live_state(cam))
                    p.hmget(keys.stream_status(cam, "main"), "status", "error", "fps", "width", "height")
                    p.hmget(keys.stream_status(cam, "sub"), "status", "error", "fps", "width", "height")
                res = await p.execute()
            state = {}
            for i, cam in enumerate(cams):
                live, mainst, subst = res[3 * i], res[3 * i + 1], res[3 * i + 2]
                state[cam] = {
                    "live": json.loads(live) if live else None,
                    "streams": {
                        k: (
                            {
                                "status": v[0],
                                "error": v[1] or None,
                                "fps": float(v[2]) if v[2] else None,
                                "width": int(v[3]) if v[3] else None,
                                "height": int(v[4]) if v[4] else None,
                            }
                            if v[0]
                            else {"status": "offline"}
                        )
                        for k, v in (("main", mainst), ("sub", subst))
                    },
                }
            try:
                c.json_q.put_nowait(json.dumps({"type": "state", "data": state}, ensure_ascii=False))
                c.wake.set()
            except asyncio.QueueFull:
                pass
        await asyncio.sleep(1.0)


async def _cleanup(c: Client, redis: Redis) -> None:
    with contextlib.suppress(Exception):
        ks = [keys.viewer(cam, prof, c.id) for cam, prof in c.subs]
        ks += [keys.consumer(cam, "main", f"ws-{c.id}") for cam, prof in c.subs if prof == "main"]
        if ks:
            await redis.delete(*ks)


async def _serve(ws: WebSocket, c: Client, reader) -> None:
    from app.core.redis import get_redis

    redis = get_redis()
    hub.ensure_started()
    hub.clients.add(c)
    tasks = [asyncio.create_task(_sender(c)), asyncio.create_task(_keepalive(c, redis)), asyncio.create_task(reader())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                log.warning("WS yopildi: %r", exc)
    finally:
        hub.clients.discard(c)
        for t in tasks:
            t.cancel()
        await _cleanup(c, redis)


@router.websocket("/api/ws/grid")
async def ws_grid(ws: WebSocket) -> None:
    await ws.accept()
    c = Client(ws)

    async def reader() -> None:
        from app.core.redis import get_redis

        redis = get_redis()
        while True:
            msg = await ws.receive_json()
            old = set(c.subs)
            if "cameras" in msg:
                c.subs = {(int(x), "grid") for x in msg["cameras"]}
            if "ai" in msg:
                c.ai = bool(msg["ai"])
            gone = old - c.subs
            if gone:
                await redis.delete(*[keys.viewer(cam, p, c.id) for cam, p in gone])
            async with redis.pipeline(transaction=False) as p:  # darhol (5 s kutmasdan)
                for cam, prof in c.subs:
                    p.set(keys.viewer(cam, prof, c.id), "1", ex=VIEWER_TTL)
                    if c.ai:
                        p.set(keys.ai_vision(cam), "1", ex=VIEWER_TTL)
                await p.execute()

    await _serve(ws, c, reader)


@router.websocket("/api/ws/camera/{camera_id}")
async def ws_camera(ws: WebSocket, camera_id: int, profile: str = "main") -> None:
    await ws.accept()
    if profile not in ("main", "analysis"):
        await ws.close(code=4400)
        return
    c = Client(ws, subs={(camera_id, profile)})

    async def reader() -> None:
        from app.core.redis import get_redis

        redis = get_redis()
        await redis.set(keys.viewer(camera_id, profile, c.id), "1", ex=VIEWER_TTL)
        if profile == "main":
            await redis.set(keys.consumer(camera_id, "main", f"ws-{c.id}"), "1", ex=VIEWER_TTL)
        while True:
            msg = await ws.receive_json()
            if "profile" in msg and msg["profile"] in ("main", "analysis"):
                await redis.delete(keys.viewer(camera_id, profile, c.id))
                c.subs = {(camera_id, msg["profile"])}
                await redis.set(keys.viewer(camera_id, msg["profile"], c.id), "1", ex=VIEWER_TTL)

    await _serve(ws, c, reader)


@router.websocket("/api/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()
    c = Client(ws)

    async def reader() -> None:
        while True:
            await ws.receive_text()

    await _serve(ws, c, reader)
