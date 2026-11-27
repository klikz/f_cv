"""inference-server: TensorRT engine menejeri va batch inference (holatsiz).

Aloqa usuli (4.1.1): kadrlar allaqachon shared memory'da — so'rovda faqat kamera, oqim, kadr raqami,
ROI kesimi va mahsulot engine'lari yuboriladi (Redis ro'yxati `fcv:inference:req`); javob
`fcv:inference:resp:<kamera>` ro'yxatiga. Kadr nusxalanmaydi, Redis orqali katta ma'lumot o'tmaydi.

- Faqat kerakli engine'lar xotirada (5 daqiqa ishlatilmasa tushiriladi).
- Bir xil engine uchun turli kameralar kesimlari bitta batch'da (maks. 8, kutish ≤ 15 ms).
- `fcv:inference:paused` (train) — engine'lar tushiriladi, so'rovlarga "paused" javobi.
- Yuklama oshsa (kechikish katta) — `fcv:inference:fps_scale` pasaytiriladi, camera-logic inference fps ni kamaytiradi.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from redis import Redis

from app.core import keys
from app.core.config import get_settings
from app.services.images import mask_outside_roi
from vision.video.shm import ReaderCache

log = logging.getLogger(__name__)

MAX_BATCH = 8
BATCH_WAIT = 0.015
IDLE_UNLOAD_SEC = 300


@dataclass
class LoadedEngine:
    path: str
    model: object
    last_used: float = field(default_factory=time.time)
    stale_warning: str | None = None


class EngineManager:
    def __init__(self) -> None:
        self.engines: dict[str, LoadedEngine] = {}
        self.lock = threading.Lock()
        self._trt_version = None
        try:
            import tensorrt

            self._trt_version = tensorrt.__version__
        except Exception:
            pass

    def get(self, path: str):
        e = self.engines.get(path)
        if e is None:
            from ultralytics import YOLO

            full = get_settings().data_path / path
            if not full.exists():
                raise FileNotFoundError(f"engine topilmadi: {path}")
            t0 = time.time()
            model = YOLO(str(full), task="detect")
            e = LoadedEngine(path, model)
            meta = full.parent / "meta.json"
            if meta.exists():
                try:
                    m = json.loads(meta.read_text())
                    if self._trt_version and m.get("trt") and m["trt"] != self._trt_version:
                        e.stale_warning = f"Engine TensorRT {m['trt']} da qurilgan, joriy {self._trt_version}"
                        log.warning(e.stale_warning)
                except Exception:
                    pass
            self.engines[path] = e
            log.info("Engine yuklandi: %s (%.1f s)", path, time.time() - t0)
        e.last_used = time.time()
        return e.model

    def unload_idle(self, force: bool = False) -> None:
        now = time.time()
        for p in [p for p, e in self.engines.items() if force or now - e.last_used > IDLE_UNLOAD_SEC]:
            self.engines.pop(p)
            log.info("Engine tushirildi: %s", p)
        if force:
            try:
                import torch

                torch.cuda.empty_cache()
            except Exception:
                pass


class InferenceServer:
    def __init__(self) -> None:
        s = get_settings()
        self.r = Redis.from_url(s.redis_url, decode_responses=True)
        self.engines = EngineManager()
        self.readers = ReaderCache()
        self.shm_names: dict[tuple[int, str], tuple[str, float]] = {}
        self.lat = deque(maxlen=200)
        self.count = 0
        self.t_stats = time.time()
        self.fps_scale = 1.0
        self.paused = False

    def _shm(self, cam: int, kind: str) -> str | None:
        k = (cam, kind)
        cached = self.shm_names.get(k)
        if cached and time.time() - cached[1] < 2:
            return cached[0]
        name = self.r.hget(keys.stream_status(cam, kind), "shm")
        self.shm_names[k] = (name or "", time.time())
        return name

    def _frame(self, cam: int, kind: str, seq: int) -> np.ndarray | None:
        rd = self.readers.get(self._shm(cam, kind))
        if rd is None:
            return None
        res = rd.read(seq, copy=False) or rd.read(copy=False)
        return None if res is None else res[2]

    def _respond(self, req: dict, payload: dict) -> None:
        key = req.get("resp") or keys.inference_resp(req["cam"])
        with self.r.pipeline(transaction=False) as p:
            p.rpush(key, json.dumps({"req_id": req.get("req_id"), "seq": req.get("seq"), **payload}))
            p.ltrim(key, -20, -1)
            p.expire(key, 10)
            p.execute()

    def _collect(self) -> list[dict]:
        first = self.r.blpop(keys.INFERENCE_REQ, timeout=1)
        if first is None:
            return []
        reqs = [json.loads(first[1])]
        deadline = time.time() + BATCH_WAIT
        while len(reqs) < 32 and time.time() < deadline:
            nxt = self.r.lpop(keys.INFERENCE_REQ)
            if nxt is None:
                time.sleep(0.002)
                continue
            reqs.append(json.loads(nxt))
        return reqs

    def process(self, reqs: list[dict]) -> None:
        now = time.time()
        fresh = []
        for rq in reqs:
            if now - rq.get("ts", now) > 2.0:  # eskirgan so'rov — kamera allaqachon keyingi kadrga o'tgan
                self._respond(rq, {"dropped": True})
            else:
                fresh.append(rq)
        if self.paused:
            for rq in fresh:
                self._respond(rq, {"paused": True})
            return
        crops: dict[int, tuple[np.ndarray, tuple[int, int, int, int], int, int]] = {}
        by_engine: dict[str, list[int]] = {}
        for i, rq in enumerate(fresh):
            fr = self._frame(rq["cam"], rq["kind"], rq["seq"])
            if fr is None:
                self._respond(rq, {"error": "kadr topilmadi"})
                continue
            h, w = fr.shape[:2]
            x1, y1, x2, y2 = rq.get("crop") or (0, 0, w, h)
            img = fr[y1:y2, x1:x2].copy() if rq.get("roi") else np.ascontiguousarray(fr[y1:y2, x1:x2])
            # train bilan bir xil: ROI poligonidan tashqarisi bo'yaladi
            mask_outside_roi(img, rq.get("roi"), (x1, y1, x2, y2), w, h)
            crops[i] = (img, (x1, y1, x2, y2), w, h)
            for pr in rq["products"]:
                by_engine.setdefault(pr["engine"], []).append(i)
        results: dict[int, list[dict]] = {i: [] for i in crops}
        errors: dict[int, str] = {}
        pid_of: dict[tuple[str, int], int] = {}
        for i in crops:
            for pr in fresh[i]["products"]:
                pid_of[(pr["engine"], i)] = pr["product_id"]
        for eng, idxs in by_engine.items():
            try:
                model = self.engines.get(eng)
            except Exception as e:
                for i in idxs:
                    errors[i] = f"engine: {e}"
                continue
            for b in range(0, len(idxs), MAX_BATCH):
                chunk = idxs[b : b + MAX_BATCH]
                conf = min(fresh[i].get("conf", 0.25) for i in chunk)
                try:
                    outs = model.predict(
                        [crops[i][0] for i in chunk],
                        imgsz=640,
                        conf=max(0.05, conf * 0.5),
                        verbose=False,
                        device=0,
                        half=True,
                    )
                except Exception as e:
                    log.exception("inference xatosi (%s)", eng)
                    for i in chunk:
                        errors[i] = str(e)
                    continue
                for i, r in zip(chunk, outs, strict=True):
                    (x1, y1, _, _), w, h = crops[i][1], crops[i][2], crops[i][3]
                    xyxy = r.boxes.xyxy.cpu().numpy() if len(r.boxes) else np.zeros((0, 4))
                    cf = r.boxes.conf.cpu().numpy() if len(r.boxes) else np.zeros((0,))
                    for bb, c in zip(xyxy, cf, strict=True):
                        results[i].append(
                            {
                                "product_id": pid_of[(eng, i)],
                                "bbox": [
                                    float((bb[0] + x1) / w),
                                    float((bb[1] + y1) / h),
                                    float((bb[2] + x1) / w),
                                    float((bb[3] + y1) / h),
                                ],
                                "conf": float(c),
                            }
                        )
        done = time.time()
        for i in crops:
            rq = fresh[i]
            self._respond(rq, {"detections": results[i], "error": errors.get(i), "latency": done - rq.get("ts", done)})
            self.lat.append(done - rq.get("ts", done))
            self.count += len(rq["products"])

    def stats(self) -> None:
        now = time.time()
        if now - self.t_stats < 2:
            return
        el = now - self.t_stats
        rps = self.count / el
        self.count, self.t_stats = 0, now
        lat = float(np.mean(self.lat)) if self.lat else 0.0
        qlen = self.r.llen(keys.INFERENCE_REQ)
        # yuklama boshqaruvi
        if lat > 0.35 or qlen > 40:
            self.fps_scale = max(0.3, self.fps_scale * 0.85)
        elif lat < 0.12 and qlen < 5:
            self.fps_scale = min(1.0, self.fps_scale * 1.05)
        vram = None
        try:
            import torch

            vram = round(torch.cuda.memory_reserved() / 2**20)
        except Exception:
            pass
        self.r.hset(
            keys.INFERENCE_STATS,
            mapping={
                "rps": round(rps, 1),
                "latency_ms": round(lat * 1000, 1),
                "queue": qlen,
                "engines": len(self.engines.engines),
                "vram_mb": vram or 0,
                "fps_scale": round(self.fps_scale, 2),
                "paused": int(self.paused),
                "ts": now,
                "stale": json.dumps([e.stale_warning for e in self.engines.engines.values() if e.stale_warning]),
            },
        )
        self.r.expire(keys.INFERENCE_STATS, 15)
        self.r.set("fcv:inference:fps_scale", round(self.fps_scale, 2), ex=15)

    def run(self, stop: threading.Event) -> None:
        log.info("inference-server tayyor")
        while not stop.is_set():
            paused = bool(self.r.exists(keys.INFERENCE_PAUSED))
            if paused and not self.paused:
                log.info("Inference to'xtatildi (train) — engine'lar tushirilmoqda")
                self.engines.unload_idle(force=True)
            elif not paused and self.paused:
                log.info("Inference qayta yoqildi")
            self.paused = paused
            try:
                reqs = self._collect()
                if reqs:
                    self.process(reqs)
            except Exception:
                log.exception("inference sikl xatosi")
                time.sleep(0.5)
            self.engines.unload_idle()
            self.stats()
        self.readers.close()


def engine_ok(path: str | None) -> bool:
    return bool(path) and (get_settings().data_path / str(path)).exists() and not str(path).endswith(".building")


_ = Path
