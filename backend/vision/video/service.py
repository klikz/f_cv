"""video-service: oqimlarni talab bo'yicha ochish, dekod (thread), shared memory'ga yozish.

- Sub oqim — har faol kamerada doim (grid uchun). Sub yo'q bo'lsa main doim ochiq.
- Main oqim — iste'molchi bo'lsa (`fcv:consumer:<cam>:main:*` TTL kalitlari): camera-logic
  (vazifa yoqilgan va tahlil oqimi main, sahifa ko'rilyapti), API (snapshot). Iste'molchi
  qolmasa `MAIN_IDLE_SEC` dan keyin yopiladi.
- Sub ishlamasa (xato) — grid uchun main ochiladi (camera-logic main dan kichraytiradi).
- Har oqim holati Redis'da: `fcv:streamstat:<cam>:<kind>` (online/connecting/offline/error).
- Kamera uzilgan oraliqlar `coverage_gaps` ga (sabab: camera).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select, update

from app.core import keys
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models.cameras import Camera, CameraStream, CoverageGap
from vision.video.decoders import FFmpegPipeDecoder, StreamError, detect_backend, open_decoder
from vision.video.shm import FrameRingWriter, cleanup_stale, segment_name

log = logging.getLogger(__name__)

MAIN_IDLE_SEC = 30.0
SUB_FAIL_FALLBACK_SEC = 8.0
TARGET_FPS = 10.0
SLOTS = 12


@dataclass
class StatusMsg:
    camera_id: int
    kind: str
    fields: dict


class StreamWorker(threading.Thread):
    """Bitta oqim: ulanish → dekod → shm; uzilsa ortib boruvchi kutish bilan qayta ulanadi."""

    _gen = 0
    _gen_lock = threading.Lock()

    def __init__(self, camera_id: int, kind: str, url: str, backend: str, out: queue.Queue[StatusMsg]) -> None:
        super().__init__(name=f"stream-{camera_id}-{kind}", daemon=True)
        self.camera_id, self.kind, self.url, self.backend = camera_id, kind, url, backend
        self.out = out
        self.stop_ev = threading.Event()
        self.writer: FrameRingWriter | None = None
        self.decoder = None
        self.status = "connecting"

    @classmethod
    def _next_gen(cls) -> int:
        with cls._gen_lock:
            cls._gen += 1
            return int(f"{os.getpid() % 100000}{cls._gen}")

    def _emit(self, **fields) -> None:
        if "status" in fields:
            self.status = fields["status"]
        self.out.put(StatusMsg(self.camera_id, self.kind, fields))

    def stop(self) -> None:
        self.stop_ev.set()
        d = self.decoder
        # PyAV konteynerini boshqa thread'dan yopib bo'lmaydi (bloklanadi) — u o'zi bayroqni ko'rib chiqadi.
        # ffmpeg processini esa darhol to'xtatish xavfsiz.
        if d is not None and isinstance(d, FFmpegPipeDecoder):
            d.close()

    def run(self) -> None:
        backoff = 1.0
        while not self.stop_ev.is_set():
            self._emit(status="connecting", error="")
            try:
                self.decoder = open_decoder(self.url, self.backend, TARGET_FPS)
                d = self.decoder
                if self.writer is None or (self.writer.w, self.writer.h) != (d.width, d.height):
                    if self.writer:
                        self.writer.close()
                    self.writer = FrameRingWriter(
                        segment_name(self.camera_id, self.kind, self._next_gen()), d.width, d.height, SLOTS
                    )
                n_out, t_last_report, first = 0, time.time(), True
                for fr in d.frames():
                    if self.stop_ev.is_set():
                        break
                    seq = self.writer.write(fr.image, fr.ts)
                    n_out += 1
                    if first:
                        first = False
                        backoff = 1.0
                        self._emit(
                            status="online",
                            error="",
                            width=d.width,
                            height=d.height,
                            codec=d.codec or "",
                            src_fps=d.src_fps or 0,
                            shm=self.writer.name,
                            backend=self.backend,
                            seq=seq,
                        )
                    now = time.time()
                    if now - t_last_report >= 2.0:
                        self._emit(fps=round(n_out / (now - t_last_report), 1), seq=seq, last_frame=fr.ts)
                        n_out, t_last_report = 0, now
            except StreamError as e:
                if not self.stop_ev.is_set():
                    log.warning("Kamera %s/%s: %s", self.camera_id, self.kind, e)
                    self._emit(status="error", error=str(e))
            except Exception as e:
                if not self.stop_ev.is_set():
                    log.exception("Kamera %s/%s: kutilmagan xato", self.camera_id, self.kind)
                    self._emit(status="error", error=f"Ichki xato: {e}")
            finally:
                if self.decoder is not None:
                    self.decoder.close()
                    self.decoder = None
            if self.stop_ev.wait(backoff):
                break
            backoff = min(backoff * 2, 30.0)
        if self.writer:
            self.writer.close()
            self.writer = None
        self._emit(status="offline", error="", shm="")


@dataclass
class CamInfo:
    id: int
    enabled: bool
    main_url: str
    sub_url: str | None
    analysis_stream: str


@dataclass
class StreamState:
    worker: StreamWorker
    url: str
    idle_since: float | None = None
    fields: dict = field(default_factory=dict)


class VideoService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        s = get_settings()
        self.backend = s.decode_backend if s.decode_backend != "auto" else detect_backend()
        self.cams: dict[int, CamInfo] = {}
        self.streams: dict[tuple[int, str], StreamState] = {}
        self.q: queue.Queue[StatusMsg] = queue.Queue()
        self.sub_error_since: dict[int, float] = {}
        self.open_gaps: dict[int, int] = {}  # camera_id -> coverage_gap id
        self._reload = asyncio.Event()
        self._was_error: set[tuple[int, str]] = set()

    async def load_cameras(self) -> None:
        async with get_sessionmaker()() as s:
            rows = (await s.execute(select(Camera))).scalars().all()
            self.cams = {
                c.id: CamInfo(c.id, c.enabled, c.main_rtsp_url, c.sub_rtsp_url, c.analysis_stream) for c in rows
            }
            gaps = (
                (
                    await s.execute(
                        select(CoverageGap).where(CoverageGap.reason == "camera", CoverageGap.end_ts.is_(None))
                    )
                )
                .scalars()
                .all()
            )
            self.open_gaps = {g.camera_id: g.id for g in gaps if g.camera_id is not None}
        log.info("Kameralar yuklandi: %d ta (dekod: %s)", len(self.cams), self.backend)

    async def _consumers(self) -> set[tuple[int, str]]:
        out: set[tuple[int, str]] = set()
        async for k in self.redis.scan_iter(match=keys.CONSUMER_PATTERN, count=500):
            parts = k.split(":")
            try:
                out.add((int(parts[2]), parts[3]))
            except (IndexError, ValueError):
                continue
        return out

    def _desired(self, consumers: set[tuple[int, str]]) -> dict[tuple[int, str], str]:
        now = time.time()
        want: dict[tuple[int, str], str] = {}
        for c in self.cams.values():
            if not c.enabled:
                continue
            if c.sub_url:
                want[(c.id, "sub")] = c.sub_url
                sub_bad = self.sub_error_since.get(c.id)
                need_main = (c.id, "main") in consumers or (
                    sub_bad is not None and now - sub_bad > SUB_FAIL_FALLBACK_SEC
                )
            else:
                need_main = True
            if need_main:
                want[(c.id, "main")] = c.main_url
        return want

    async def reconcile(self) -> None:
        consumers = await self._consumers()
        want = self._desired(consumers)
        now = time.time()
        # yangi / manzili o'zgarganlar
        for key, url in want.items():
            st = self.streams.get(key)
            if st is not None and st.url != url:
                await self._stop(key)
                st = None
            if st is None:
                w = StreamWorker(key[0], key[1], url, self.backend, self.q)
                self.streams[key] = StreamState(w, url)
                w.start()
                log.info("Oqim ochildi: kamera %s / %s", *key)
            else:
                st.idle_since = None
        # keraksizlar
        for key in list(self.streams):
            if key in want:
                continue
            st = self.streams[key]
            cam = self.cams.get(key[0])
            immediate = cam is None or not cam.enabled or key[1] == "sub"
            if immediate:
                await self._stop(key)
                continue
            if st.idle_since is None:
                st.idle_since = now
            elif now - st.idle_since >= MAIN_IDLE_SEC:
                await self._stop(key)

    async def _stop(self, key: tuple[int, str]) -> None:
        st = self.streams.pop(key, None)
        if st is None:
            return
        st.worker.stop()
        await asyncio.to_thread(st.worker.join, 8)
        log.info("Oqim yopildi: kamera %s / %s", *key)
        await self.redis.delete(keys.stream_status(*key))
        await self.redis.publish(
            keys.CH_STREAM_STATUS, json.dumps({"camera_id": key[0], "kind": key[1], "status": "offline"})
        )

    async def drain_status(self) -> None:
        while True:
            try:
                msg = self.q.get_nowait()
            except queue.Empty:
                return
            key = (msg.camera_id, msg.kind)
            st = self.streams.get(key)
            if st is None and msg.fields.get("status") != "offline":
                continue
            rkey = keys.stream_status(*key)
            f = {k: ("" if v is None else v) for k, v in msg.fields.items()}
            f["updated"] = time.time()
            prev_status = st.fields.get("status") if st else None
            if st:
                st.fields.update(f)
            if msg.fields.get("status") == "offline":
                continue  # _stop o'zi tozalaydi
            await self.redis.hset(rkey, mapping=f)
            await self.redis.expire(rkey, 60)
            new_status = msg.fields.get("status")
            if new_status and new_status != prev_status:
                await self.redis.publish(
                    keys.CH_STREAM_STATUS,
                    json.dumps(
                        {
                            "camera_id": msg.camera_id,
                            "kind": msg.kind,
                            "status": new_status,
                            "error": msg.fields.get("error", ""),
                        }
                    ),
                )
                await self._on_status_change(msg.camera_id, msg.kind, new_status, msg.fields)

    async def _on_status_change(self, camera_id: int, kind: str, status: str, fields: dict) -> None:
        cam = self.cams.get(camera_id)
        if kind == "sub":
            if status == "error":
                self.sub_error_since.setdefault(camera_id, time.time())
            elif status == "online":
                self.sub_error_since.pop(camera_id, None)
        async with get_sessionmaker()() as s:
            vals: dict = {"status": status, "updated_at": datetime.now(UTC)}
            if status == "online":
                vals.update(
                    codec=fields.get("codec") or None,
                    width=fields.get("width"),
                    height=fields.get("height"),
                    fps=fields.get("src_fps") or None,
                    last_error=None,
                )
            elif status == "error":
                vals["last_error"] = fields.get("error")
            res = await s.execute(
                update(CameraStream)
                .where(CameraStream.camera_id == camera_id, CameraStream.kind == kind)
                .values(**vals)
            )
            if res.rowcount == 0:
                s.add(CameraStream(camera_id=camera_id, kind=kind, **vals))
            # coverage_gaps: kameraning tahlil oqimi bo'yicha
            if cam and kind == cam.analysis_stream:
                now = datetime.now(UTC)
                if status == "error" and camera_id not in self.open_gaps:
                    g = CoverageGap(camera_id=camera_id, reason="camera", start_ts=now, detail=fields.get("error"))
                    s.add(g)
                    await s.flush()
                    self.open_gaps[camera_id] = g.id
                elif status == "online" and camera_id in self.open_gaps:
                    gid = self.open_gaps.pop(camera_id)
                    await s.execute(update(CoverageGap).where(CoverageGap.id == gid).values(end_ts=now))
            await s.commit()
        if status == "error":
            self._was_error.add((camera_id, kind))
        elif status == "online":
            if (camera_id, kind) not in self._was_error:
                return  # oddiy ulanish (ishga tushish) — "tiklandi" emas
            self._was_error.discard((camera_id, kind))
        if status in ("error", "online"):
            from app.services import bus

            # Telegram/UI: kamera uzildi / tiklandi (faqat tahlil yoki grid oqimi uchun bir marta)
            main_kind = "sub" if cam and cam.sub_url else "main"
            if kind == main_kind:
                from app.services.system_events import record_sync

                await asyncio.to_thread(
                    record_sync,
                    "camera_offline" if status == "error" else "camera_online",
                    f"Kamera #{camera_id} {'uzildi' if status == 'error' else 'tiklandi'}"
                    + (f": {fields.get('error')}" if status == "error" else ""),
                    level="warning" if status == "error" else "info",
                    source="video-service",
                    data={"camera_id": camera_id},
                )
                await bus.emit_event(
                    self.redis,
                    "camera_offline" if status == "error" else "camera_online",
                    {"camera_id": camera_id, "error": fields.get("error", "")},
                    durable=True,
                )

    async def listen_changes(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(keys.CH_CAMERAS)
        try:
            async for m in pubsub.listen():
                if m.get("type") == "message":
                    self._reload.set()
        finally:
            await pubsub.aclose()

    async def run(self, stop: asyncio.Event) -> None:
        n = cleanup_stale()
        if n:
            log.info("Eski shared memory segmentlari tozalandi: %d", n)
        await self.load_cameras()
        listener = asyncio.create_task(self.listen_changes())
        try:
            while not stop.is_set():
                if self._reload.is_set():
                    self._reload.clear()
                    await self.load_cameras()
                await self.reconcile()
                await self.drain_status()
                await self._publish_summary()
                try:
                    await asyncio.wait_for(stop.wait(), 1.0)
                except TimeoutError:
                    pass
        finally:
            listener.cancel()
            for key in list(self.streams):
                await self._stop(key)

    async def _publish_summary(self) -> None:
        await self.redis.hset(
            "fcv:video:summary",
            mapping={"backend": self.backend, "streams": len(self.streams), "ts": time.time()},
        )
