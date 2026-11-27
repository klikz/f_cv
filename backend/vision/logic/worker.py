"""camera-logic (bitta kamera): kadr o'qish, vazifalar (sanash, uskuna), JPEG + metadata.

JPEG faqat kimdir ko'rayotgan bo'lsa tayyorlanadi (`fcv:viewer:<cam>:<profil>:*` kalitlari):
  grid     — sub oqimdan (sub yo'q/ishlamasa main dan), ≈640×360, 4 fps; metadata faqat AI Vision yoqilsa
  main     — kamera sahifasi, main oqimdan, 1280×720, 10 fps
  analysis — sozlash sahifalari, kameraning tahlil oqimidan, 10 fps
Xabar: [4 bayt sarlavha uzunligi][JSON sarlavha][JPEG] — kadr va metadata doim mos.
"""

from __future__ import annotations

import json
import logging
import struct
import time
from typing import Any, Protocol

import cv2
import numpy as np
from redis import Redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core import keys
from app.core.config import get_settings
from app.models.cameras import Camera
from app.models.tasks import CameraTask, CountingConfig, EquipmentConfig
from vision.logic.frames import FrameSource

log = logging.getLogger(__name__)

PROFILES = {
    "grid": {"fps": 4.0, "size": (640, 360), "quality": 70},
    "main": {"fps": 10.0, "size": (1280, 720), "quality": 80},
    "analysis": {"fps": 10.0, "size": (1280, 720), "quality": 80},
}
CONSUMER_TTL = 12


class TaskProcessor(Protocol):
    task_type: str

    def process(self, seq: int, ts: float, frame: np.ndarray) -> None: ...

    def overlay(self) -> dict[str, Any]: ...

    def live(self) -> dict[str, Any]: ...

    def tick(self, now: float) -> None: ...

    def reload(self, cfg: Any) -> None: ...

    def on_stream_lost(self) -> None: ...

    def close(self) -> None: ...


def sync_db_url() -> str:
    """camera-logic sinxron (thread) ishlaydi — psycopg drayveri bilan."""
    return get_settings().database_url.replace("postgresql+asyncpg", "postgresql+psycopg")


def encode_message(header: dict[str, Any], jpeg: bytes) -> bytes:
    h = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
    return struct.pack(">I", len(h)) + h + jpeg


class CameraLogic:
    def __init__(self, camera_id: int) -> None:
        self.camera_id = camera_id
        s = get_settings()
        self.r = Redis.from_url(s.redis_url, decode_responses=True)
        self.rb = Redis.from_url(s.redis_url, decode_responses=False)  # ikkilik xabarlar uchun
        self.engine = create_engine(sync_db_url(), pool_pre_ping=True, pool_size=2)
        self.src = FrameSource(self.r, camera_id)
        self.cam: Camera | None = None
        self.tasks: dict[str, TaskProcessor] = {}
        self.enabled_tasks: set[str] = set()
        self.viewers: dict[str, bool] = {p: False for p in PROFILES}
        self.ai_vision = False
        self._next_jpeg: dict[str, float] = {p: 0.0 for p in PROFILES}
        self._last_viewer_scan = 0.0
        self._last_consumer = 0.0
        self._last_live = 0.0
        self._reload_requested = True
        self.autocollect: dict = {}
        self.collector = None
        self.test_mode = False
        self._last_testmode_check = 0.0
        self.pubsub = self.r.pubsub(ignore_subscribe_messages=True)
        self.pubsub.subscribe(keys.CH_TASKS, keys.CH_CAMERAS)

    # --- konfiguratsiya ---
    def load(self) -> None:
        with Session(self.engine) as s:
            cam = s.get(Camera, self.camera_id)
            if cam is None:
                self.cam = None
                return
            s.expunge(cam)
            self.cam = cam
            rows = s.execute(select(CameraTask).where(CameraTask.camera_id == self.camera_id)).scalars().all()
            self.enabled_tasks = {t.task_type for t in rows if t.enabled}
            ccfg = s.get(CountingConfig, self.camera_id)
            ecfg = s.get(EquipmentConfig, self.camera_id)
            for c in (ccfg, ecfg):
                if c is not None:
                    s.expunge(c)
            from app.models.settings import Setting

            ac = s.get(Setting, "dataset.autocollect")
            self.autocollect = ((ac.value or {}) if ac else {}).get(str(self.camera_id)) or {}
            from app.services.images import IMAGES_ROOT_KEY, resolve_images_root

            ir = s.get(Setting, IMAGES_ROOT_KEY)
            self.images_root = resolve_images_root(ir.value if ir else None)
        self.test_mode = bool(self.r.exists(f"fcv:testmode:{self.camera_id}"))
        self._apply_tasks(ccfg, ecfg)
        from vision.logic.autocollect import AutoCollector

        if self.autocollect.get("enabled"):
            if self.collector is None:
                self.collector = AutoCollector(self)
            self.collector.configure(
                self.autocollect, ccfg.roi_polygon if ccfg else (ecfg.roi_polygon if ecfg else None)
            )
        else:
            self.collector = None
        log.info(
            "Sozlama yuklandi: tahlil oqimi=%s, vazifalar=%s", self.cam.analysis_stream, sorted(self.enabled_tasks)
        )

    def _apply_tasks(self, ccfg: CountingConfig | None, ecfg: EquipmentConfig | None) -> None:
        wanted = {
            "counting": ccfg
            if ("counting" in self.enabled_tasks and ccfg and ccfg.roi_polygon and ccfg.line)
            else None,
            "equipment": ecfg if ("equipment" in self.enabled_tasks and ecfg and ecfg.roi_polygon) else None,
        }
        for tt, cfg in wanted.items():
            cur = self.tasks.get(tt)
            if cfg is None:
                if cur is not None:
                    cur.close()
                    del self.tasks[tt]
                continue
            if cur is None:
                proc = self._make_task(tt, cfg)
                if proc is not None:
                    self.tasks[tt] = proc
                    cur = proc
            else:
                cur.reload(cfg)
            if tt == "counting" and cur is not None:
                cur.dry_run = "counting" not in self.enabled_tasks  # jonli test: bazaga yozilmaydi

    def _make_task(self, task_type: str, cfg: Any) -> TaskProcessor | None:
        try:
            if task_type == "counting":
                from vision.logic.counting import CountingTask

                return CountingTask(self, cfg)
            if task_type == "equipment":
                from vision.motion.equipment import EquipmentTask

                return EquipmentTask(self, cfg)
        except ImportError:
            return None
        except Exception:
            log.exception("Vazifani yaratib bo'lmadi: %s", task_type)
        return None

    @property
    def analysis_kind(self) -> str:
        if self.cam is None:
            return "main"
        if self.cam.analysis_stream == "sub" and self.cam.sub_rtsp_url:
            return "sub"
        return "main"

    # --- iste'molchi/tomoshabin ---
    def _scan_viewers(self, now: float) -> None:
        if now - self._last_viewer_scan < 1.0:
            return
        self._last_viewer_scan = now
        for p in PROFILES:
            self.viewers[p] = (
                next(self.r.scan_iter(match=keys.viewer_pattern(self.camera_id, p), count=100), None) is not None
            )
        self.ai_vision = bool(self.r.exists(keys.ai_vision(self.camera_id)))

    def _grid_kind(self) -> str:
        assert self.cam is not None
        # AI Vision yoqilgan, tahlil main va ko'rish maydoni farqli — katakni main dan ko'rsatamiz (fov_match qoidasi)
        if self.ai_vision and self.analysis_kind == "main" and not self.cam.fov_match and self.tasks:
            return "main"
        if self.cam.sub_rtsp_url and self.src.online("sub"):
            return "sub"
        return "main"

    def _needs_main(self) -> bool:
        if self.cam is None:
            return False
        if self.viewers["main"]:
            return True
        if self.analysis_kind == "main" and (self.tasks or self.viewers["analysis"] or self.collector):
            return True
        return bool(self.viewers["grid"] and self._grid_kind() == "main")

    def _register_consumer(self, now: float) -> None:
        need = self._needs_main()
        changed = need != getattr(self, "_last_need", None)
        self._last_need = need
        if not changed and now - self._last_consumer < 3.0:
            return
        self._last_consumer = now
        if need:
            self.r.set(keys.consumer(self.camera_id, "main", "logic"), "1", ex=CONSUMER_TTL)

    # --- JPEG ---
    def _overlay(self, profile: str, frame_kind: str) -> dict[str, Any]:
        if profile == "grid" and not self.ai_vision:
            return {}
        out: dict[str, Any] = {"space": self.analysis_kind}
        for t in self.tasks.values():
            try:
                out[t.task_type] = t.overlay()
            except Exception:
                log.exception("overlay xatosi")
        out["frame_kind"] = frame_kind
        return out

    def _publish_jpeg(self, profile: str, now: float) -> None:
        if not self.viewers[profile] or now < self._next_jpeg[profile]:
            return
        cfg = PROFILES[profile]
        kind = {"grid": self._grid_kind(), "main": "main", "analysis": self.analysis_kind}[profile]
        if profile == "main" and not self.src.online("main") and self.src.online("sub"):
            kind = "sub"  # main ochilguncha sub kadri (kutish ekrani o'rniga)
        res = self.src.latest(kind)
        if res is None:
            return
        self._next_jpeg[profile] = now + 1.0 / cfg["fps"]
        seq, ts, img = res
        h, w = img.shape[:2]
        tw, th = cfg["size"]
        scale = min(tw / w, th / h, 1.0)
        if scale < 1.0:
            img = cv2.resize(img, (int(w * scale) // 2 * 2, int(h * scale) // 2 * 2), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, cfg["quality"]])
        if not ok:
            return
        header = {
            "cam": self.camera_id,
            "profile": profile,
            "stream": kind,
            "seq": seq,
            "ts": ts,
            "w": img.shape[1],
            "h": img.shape[0],
            "src_w": w,
            "src_h": h,
            "meta": self._overlay(profile, kind),
        }
        self.rb.publish(keys.ch_frames(self.camera_id, profile), encode_message(header, buf.tobytes()))

    def _publish_live(self, now: float) -> None:
        if now - self._last_live < 1.0:
            return
        self._last_live = now
        state: dict[str, Any] = {"ts": now, "tasks": sorted(self.tasks), "enabled": sorted(self.enabled_tasks)}
        for t in self.tasks.values():
            try:
                state[t.task_type] = t.live()
            except Exception:
                log.exception("live xatosi")
        self.r.set(keys.live_state(self.camera_id), json.dumps(state, ensure_ascii=False, default=str), ex=10)

    # --- asosiy sikl ---
    def _handle_messages(self) -> None:
        while True:
            m = self.pubsub.get_message(timeout=0)
            if m is None:
                return
            try:
                data = json.loads(m["data"])
            except (TypeError, ValueError):
                continue
            if data.get("camera_id") in (self.camera_id, 0, None):
                self._reload_requested = True

    def run(self, stop) -> None:
        analysis_lost_at: float | None = None
        while not stop.is_set():
            t0 = time.time()
            self._handle_messages()
            if self._reload_requested:
                self._reload_requested = False
                self.load()
                self.src.refresh(force=True)
            if self.cam is None:
                time.sleep(1)
                continue
            self.src.refresh()
            self._scan_viewers(t0)
            self._register_consumer(t0)
            # jonli test rejimi o'zgardimi
            if t0 - self._last_testmode_check > 2:
                self._last_testmode_check = t0
                if bool(self.r.exists(f"fcv:testmode:{self.camera_id}")) != self.test_mode:
                    self._reload_requested = True
            # vazifalar — tahlil oqimining har yangi kadri
            if self.tasks or self.collector:
                res = self.src.latest(self.analysis_kind, only_new=True, copy=False)
                if res is not None and self.collector is not None:
                    try:
                        self.collector.process(res[0], res[1], res[2])
                    except Exception:
                        log.exception("avto-yig'ish xatosi")
                if res is not None:
                    analysis_lost_at = None
                    seq, ts, frame = res
                    for t in list(self.tasks.values()):
                        try:
                            t.process(seq, ts, frame)
                        except Exception:
                            log.exception("%s: kadrni qayta ishlashda xato", t.task_type)
                elif not self.src.online(self.analysis_kind):
                    if analysis_lost_at is None:
                        analysis_lost_at = t0
                    elif t0 - analysis_lost_at > 5:
                        for t in self.tasks.values():
                            t.on_stream_lost()
                for t in list(self.tasks.values()):
                    try:
                        t.tick(t0)
                    except Exception:
                        log.exception("%s: tick xatosi", t.task_type)
            for p in PROFILES:
                try:
                    self._publish_jpeg(p, t0)
                except Exception:
                    log.exception("JPEG xatosi (%s)", p)
            self._publish_live(t0)
            dt = time.time() - t0
            time.sleep(max(0.0, 0.03 - dt))

    def close(self) -> None:
        for t in self.tasks.values():
            try:
                t.close()
            except Exception:
                log.exception("vazifani yopishda xato")
        self.src.close()
        self.pubsub.close()
        self.engine.dispose()
