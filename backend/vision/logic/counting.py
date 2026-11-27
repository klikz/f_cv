"""Mahsulot sanash vazifasi (camera-logic ichida, PLAN.md 1.7).

Zanjir: tahlil oqimi kadri → mavjudlik filtri → inference-server (faol mahsulot engine'lari) →
ROI filtri → turli modellar ramkalarini birlashtirish → ByteTrack → mahsulotlar bo'yicha ball yig'ish →
chiziq kesish (burchak, yosh, histerezis) → g'olib + o'lcham tekshiruvi → "noaniq" qarori →
`count_events` (smena bilan) + snapshot + Redis hodisasi (UI va Telegram).

Snapshot sifatida **toza kadr** saqlanadi, ramka koordinatasi bazada: UI va Telegram ramkani chizib ko'rsatadi
(datasetga qo'shish uchun toza rasm kerak; disk ikki barobar tejaladi).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import cv2
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import keys
from app.models.catalog import ModelVersion, Product
from app.models.counting import CountEvent, CountingConfigProduct
from app.models.shifts import Shift
from app.models.tasks import CountingConfig
from app.services.images import roi_crop_box, save_jpeg, task_dir
from app.services.shifts import ShiftDef, match_shift
from vision.logic.geometry import CrossingState, LineCounter, iou_matrix, point_in_polygon
from vision.logic.tracker import ByteTracker, Track

log = logging.getLogger(__name__)


class SyncShifts:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.defs: list[ShiftDef] = []
        self.loaded = 0.0

    def match(self, ts: datetime):
        if time.time() - self.loaded > 60:
            with Session(self.engine) as s:
                rows = s.execute(select(Shift)).scalars().all()
                self.defs = [ShiftDef(r.id, r.name, r.start_time, r.end_time, r.effective_from) for r in rows]
            self.loaded = time.time()
        return match_shift(self.defs, ts)


def merge_detections(dets: list[dict], iou_thr: float = 0.5) -> list[dict]:
    """Turli mahsulot modellarining ustma-ust ramkalari → bitta fizik obyekt (ballar mahsulot bo'yicha)."""
    if not dets:
        return []
    dets = sorted(dets, key=lambda d: -d["conf"])
    boxes = np.array([d["box"] for d in dets], dtype=np.float32)
    iou = iou_matrix(boxes, boxes)
    used = [False] * len(dets)
    out = []
    for i, d in enumerate(dets):
        if used[i]:
            continue
        group = [j for j in range(len(dets)) if not used[j] and iou[i, j] >= iou_thr]
        scores: dict[int, float] = {}
        for j in group:
            used[j] = True
            pid = dets[j]["product_id"]
            scores[pid] = max(scores.get(pid, 0.0), dets[j]["conf"])
        out.append({"box": d["box"], "conf": d["conf"], "scores": scores})
    return out


def decide(
    scores_sum: dict[int, float],
    updates: int,
    area: float | None,
    sizes: dict[int, tuple[float | None, float | None]],
    margin_thr: float,
    min_score: float,
) -> tuple[int | None, str, list[dict]]:
    """G'olib mahsulot va holat ('confirmed' | 'uncertain'), nomzodlar ro'yxati."""
    if not scores_sum:
        return None, "uncertain", []
    n = max(1, updates)
    ranked = sorted(scores_sum.items(), key=lambda kv: -kv[1])
    cands = [{"product_id": pid, "score": round(s / n, 3)} for pid, s in ranked]

    def in_range(pid: int) -> bool | None:
        lo, hi = sizes.get(pid, (None, None))
        if area is None or lo is None or hi is None:
            return None
        return lo <= area <= hi

    winner, s1 = ranked[0]
    reasons = []
    if in_range(winner) is False:
        alt = next(((pid, s) for pid, s in ranked[1:] if in_range(pid) is True and s >= 0.5 * s1), None)
        if alt:
            winner, s1 = alt
            reasons.append("size_switch")
        else:
            reasons.append("size_out")
    second = max((s for pid, s in ranked if pid != winner), default=0.0)
    margin = (s1 - second) / s1 if s1 > 0 else 0.0
    avg = s1 / n
    status = "confirmed"
    if (second > 0 and margin < margin_thr) or avg < min_score or "size_out" in reasons:
        status = "uncertain"
    for c in cands:
        c["winner"] = c["product_id"] == winner
    return winner, status, cands


class CountingTask:
    task_type = "counting"

    def __init__(self, logic, cfg: CountingConfig) -> None:
        self.logic = logic
        self.cam_id = logic.camera_id
        self.r = logic.r
        self.engine = logic.engine
        self.shifts = SyncShifts(self.engine)
        self.tracker = ByteTracker()
        self.cfg: CountingConfig = cfg
        self.products: list[dict] = []
        self.names: dict[int, str] = {}
        self.sizes: dict[int, tuple[float | None, float | None]] = {}
        self.totals: dict[int | None, int] = defaultdict(int)
        self.reverse_totals: dict[int | None, int] = defaultdict(int)
        self.uncertain = 0
        self.shift_key: tuple | None = None
        self.next_inf = 0.0
        self.prev_small: np.ndarray | None = None
        self.paused = False
        self.paused_reason: str | None = None
        self.last_pause_check = 0.0
        self.flash_until = 0.0
        self.last_event: dict | None = None
        self.overlay_dets: list[dict] = []
        self.frame_wh: tuple[int, int] | None = None
        self.dry_run = False
        self.last_error: str | None = None
        self.reload(cfg)
        self._restore_totals()

    # ---------- konfiguratsiya ----------
    def reload(self, cfg: CountingConfig) -> None:
        geom_changed = (cfg.roi_polygon, cfg.line) != (self.cfg.roi_polygon, self.cfg.line)
        self.cfg = cfg
        if geom_changed:
            self.tracker.reset()
        with Session(self.engine) as s:
            self.names = dict(s.execute(select(Product.id, Product.name)).all())
            rows = (
                s.execute(select(CountingConfigProduct).where(CountingConfigProduct.camera_id == self.cam_id))
                .scalars()
                .all()
            )
            prods = []
            for row in rows:
                mv = None
                if row.model_version_id:
                    mv = s.get(ModelVersion, row.model_version_id)
                if mv is None:
                    # kameraga xos faol versiya, bo'lmasa umumiy faol versiya
                    mv = (
                        s.execute(
                            select(ModelVersion)
                            .where(
                                ModelVersion.product_id == row.product_id,
                                ModelVersion.is_active.is_(True),
                                (ModelVersion.camera_id == self.cam_id) | ModelVersion.camera_id.is_(None),
                            )
                            .order_by(ModelVersion.camera_id.is_(None))
                        )
                        .scalars()
                        .first()
                    )
                if mv and mv.engine_path and mv.status == "ready":
                    prods.append({"product_id": row.product_id, "engine": mv.engine_path, "version": mv.version})
                self.sizes[row.product_id] = (row.size_min, row.size_max)
            self.products = prods
        log.info("Sanash: %d ta faol mahsulot modeli", len(self.products))

    def _restore_totals(self) -> None:
        """Qayta ishga tushganda joriy smena sanoqlarini bazadan tiklash (4.2.13)."""
        m = self.shifts.match(datetime.now(UTC))
        self.shift_key = (m.shift_id, m.shift_date) if m else None
        self.totals.clear()
        self.reverse_totals.clear()
        self.uncertain = 0
        if not m:
            return
        with Session(self.engine) as s:
            rows = s.execute(
                select(CountEvent.product_id, CountEvent.direction, CountEvent.status, func.count())
                .where(
                    CountEvent.camera_id == self.cam_id,
                    CountEvent.shift_id == m.shift_id,
                    CountEvent.shift_date == m.shift_date,
                    CountEvent.status != "cancelled",
                )
                .group_by(CountEvent.product_id, CountEvent.direction, CountEvent.status)
            ).all()
        for pid, direction, status, n in rows:
            self._apply_total(pid, direction, n)
            if status == "uncertain":
                self.uncertain += n

    def _apply_total(self, pid: int | None, direction: str, n: int = 1) -> None:
        pol = self.cfg.reverse_policy
        if direction == "forward" or self.cfg.direction == "both":
            if direction == "reverse":
                self.reverse_totals[pid] += n
            else:
                self.totals[pid] += n
        elif pol == "subtract":
            self.totals[pid] -= n
        else:
            self.reverse_totals[pid] += n

    # ---------- asosiy ----------
    def _check_pause(self, now: float) -> None:
        if now - self.last_pause_check < 1.0:
            return
        self.last_pause_check = now
        reason = self.r.get(keys.INFERENCE_PAUSED)
        if bool(reason) != self.paused:
            self.paused = bool(reason)
            self.paused_reason = reason
            self.tracker.reset()
            self.overlay_dets = []
        # smena almashdi — hisoblagichlar noldan (7.1.5)
        m = self.shifts.match(datetime.now(UTC))
        key = (m.shift_id, m.shift_date) if m else None
        if key != self.shift_key:
            self._restore_totals()

    def tick(self, now: float) -> None:
        self._check_pause(now)

    def on_stream_lost(self) -> None:
        self.tracker.reset()
        self.overlay_dets = []

    def _fps(self) -> float:
        try:
            scale = float(self.r.get("fcv:inference:fps_scale") or 1.0)
        except ValueError:
            scale = 1.0
        return max(0.5, float(self.cfg.inference_fps) * scale)

    def process(self, seq: int, ts: float, frame: np.ndarray) -> None:
        now = time.time()
        if self.paused or not self.products or now < self.next_inf:
            return
        self.next_inf = now + 1.0 / self._fps()
        h, w = frame.shape[:2]
        self.frame_wh = (w, h)
        roi_px = [(x * w, y * h) for x, y in self.cfg.roi_polygon or []]
        crop = roi_crop_box(self.cfg.roi_polygon, w, h)
        # mavjudlik filtri: ROI da harakat ham, faol track ham bo'lmasa — inference yo'q
        x1, y1, x2, y2 = crop
        small = cv2.resize(
            cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY), (96, 54), interpolation=cv2.INTER_AREA
        )
        motion = 255.0 if self.prev_small is None else float(np.mean(cv2.absdiff(small, self.prev_small)))
        self.prev_small = small
        if motion < 1.2 and not self.tracker.tracks:
            self.overlay_dets = []
            return
        dets = self._infer(seq, crop)
        if dets is None:
            return
        # ROI filtri
        objs = []
        for d in dets:
            bx = [d["bbox"][0] * w, d["bbox"][1] * h, d["bbox"][2] * w, d["bbox"][3] * h]
            if d["conf"] < self.cfg.conf_threshold * 0.5:
                continue
            c = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
            if roi_px and not point_in_polygon(c, roi_px):
                continue
            objs.append({"box": bx, "conf": d["conf"], "product_id": d["product_id"]})
        merged = merge_detections(objs)
        arr = np.array([[*m["box"], m["conf"]] for m in merged], dtype=np.float64).reshape(-1, 5)
        active, matched = self.tracker.update(arr)
        for t, di in matched:
            meta = t.meta
            meta.setdefault("scores", defaultdict(float))
            meta["updates"] = meta.get("updates", 0) + 1
            for pid, sc in merged[di]["scores"].items():
                meta["scores"][pid] += sc
            area = (t.box[2] - t.box[0]) * (t.box[3] - t.box[1]) / (w * h)
            meta.setdefault("areas", []).append(area)
        self._crossings(active, frame, w, h)
        self.overlay_dets = [self._det_overlay(t, w, h) for t in active]

    def _infer(self, seq: int, crop: tuple[int, int, int, int]) -> list[dict] | None:
        req_id = uuid.uuid4().hex[:10]
        resp_key = keys.inference_resp(self.cam_id)
        req = {
            "cam": self.cam_id,
            "kind": self.logic.analysis_kind,
            "seq": seq,
            "crop": list(crop),
            "products": self.products,
            "conf": float(self.cfg.conf_threshold),
            "ts": time.time(),
            "req_id": req_id,
            "resp": resp_key,
        }
        self.r.rpush(keys.INFERENCE_REQ, json.dumps(req))
        deadline = time.time() + 1.5
        while time.time() < deadline:
            res = self.r.blpop(resp_key, timeout=max(0.05, deadline - time.time()))
            if res is None:
                break
            data = json.loads(res[1])
            if data.get("req_id") != req_id:
                continue
            if data.get("paused"):
                self.paused = True
                return None
            if data.get("error"):
                if data["error"] != self.last_error:
                    log.warning("inference xatosi: %s", data["error"])
                self.last_error = data["error"]
            return data.get("detections") or []
        self.last_error = "inference-server javob bermadi"
        return None

    def _point(self, t: Track) -> tuple[float, float]:
        x1, y1, x2, y2 = t.box
        if self.cfg.track_point == "bottom_center":
            return ((x1 + x2) / 2, y2)
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _crossings(self, active: list[Track], frame: np.ndarray, w: int, h: int) -> None:
        if not self.cfg.line:
            return
        a = (self.cfg.line[0][0] * w, self.cfg.line[0][1] * h)
        b = (self.cfg.line[1][0] * w, self.cfg.line[1][1] * h)
        lc = LineCounter(
            a,
            b,
            max_angle=float(self.cfg.max_angle),
            min_track_frames=int(self.cfg.min_track_frames),
            min_distance=float(self.cfg.min_distance) * float(np.hypot(w, h)),
        )
        counted_dir = {"a_to_b": 1, "b_to_a": -1, "both": 0}[self.cfg.direction]
        for t in active:
            st: CrossingState = t.meta.setdefault("cross", CrossingState())
            d = lc.update(st, self._point(t), t.age)
            if d is None:
                continue
            forward = counted_dir == 0 or d == counted_dir
            pol = self.cfg.reverse_policy
            n_counts = t.meta.get("n_counts", 0)
            if forward:
                if self.cfg.direction != "both" and pol == "ignore" and n_counts > 0:
                    continue
                t.meta["n_counts"] = n_counts + 1
                self._record(t, frame, w, h, "forward" if (counted_dir != 0 or d == 1) else "reverse")
            else:
                if self.cfg.direction == "both":
                    continue
                if pol == "ignore" or (n_counts == 0 and pol == "subtract"):
                    continue
                self._record(t, frame, w, h, "reverse")

    def _record(self, t: Track, frame: np.ndarray, w: int, h: int, direction: str) -> None:
        meta = t.meta
        areas = meta.get("areas") or []
        area = float(np.median(areas)) if areas else None
        pid, status, cands = decide(
            dict(meta.get("scores", {})),
            meta.get("updates", 0),
            area,
            self.sizes,
            float(self.cfg.uncertain_margin),
            float(self.cfg.min_winner_score),
        )
        meta["counted"] = True
        meta["label"] = self.names.get(pid or 0, "Noaniq")
        self.flash_until = time.time() + 0.8
        bbox = [
            round(float(t.box[0] / w), 5),
            round(float(t.box[1] / h), 5),
            round(float(t.box[2] / w), 5),
            round(float(t.box[3] / h), 5),
        ]
        conf = next((c["score"] for c in cands if c.get("winner")), None)
        name = self.names.get(pid or 0, "Noaniq")
        self.last_event = {"ts": time.time(), "product": name, "status": status}
        if self.dry_run:
            return
        now = datetime.now(UTC)
        m = self.shifts.match(now)
        try:
            rel = save_jpeg(frame, task_dir(self.logic.images_root, self.cam_id, "counting") / "snapshots", quality=85)
        except Exception:
            log.exception("snapshot saqlanmadi")
            rel = None
        with Session(self.engine) as s:
            ev = CountEvent(
                camera_id=self.cam_id,
                product_id=pid,
                original_product_id=pid,
                status=status,
                candidates=cands,
                direction=direction,
                confidence=conf,
                bbox=bbox,
                track_id=t.id,
                ts=now,
                shift_id=m.shift_id if m else None,
                shift_date=m.shift_date if m else None,
                snapshot_path=rel,
            )
            s.add(ev)
            s.commit()
            ev_id = ev.id
        self._apply_total(pid, direction)
        if status == "uncertain":
            self.uncertain += 1
        total = self.totals.get(pid, 0)
        payload = {
            "kind": "count",
            "ts": time.time(),
            "event_id": ev_id,
            "camera_id": self.cam_id,
            "product_id": pid,
            "product": name,
            "status": status,
            "direction": direction,
            "shift_total": total,
            "camera_total": sum(self.totals.values()),
            "snapshot": rel,
        }
        data = json.dumps(payload, ensure_ascii=False)
        with self.r.pipeline(transaction=False) as p:
            p.publish(keys.CH_EVENTS, data)
            p.xadd(keys.STREAM_EVENTS, {"data": data}, maxlen=100_000, approximate=True)
            p.execute()
        log.info("Sanoq #%s: %s (%s, %s) track %s", ev_id, name, status, direction, t.id)

    def _det_overlay(self, t: Track, w: int, h: int) -> dict:
        scores = t.meta.get("scores") or {}
        n = max(1, t.meta.get("updates", 1))
        if scores:
            pid, s = max(scores.items(), key=lambda kv: kv[1])
            label = self.names.get(pid, f"#{pid}")
            sc = s / n
        else:
            label, sc = "?", t.score
        if t.meta.get("counted"):
            label = t.meta.get("label", label)
        return {
            "bbox": [float(t.box[0] / w), float(t.box[1] / h), float(t.box[2] / w), float(t.box[3] / h)],
            "label": label,
            "score": round(float(sc), 2),
            "track_id": t.id,
            "counted": bool(t.meta.get("counted")),
        }

    def overlay(self) -> dict[str, Any]:
        return {
            "roi": self.cfg.roi_polygon,
            "line": self.cfg.line,
            "direction": self.cfg.direction,
            "detections": self.overlay_dets,
            "flash": time.time() < self.flash_until,
            "paused": self.paused,
        }

    def live(self) -> dict[str, Any]:
        per = [
            {"product_id": pid, "name": self.names.get(pid or 0, "Noaniq"), "count": n}
            for pid, n in self.totals.items()
            if n
        ]
        per.sort(key=lambda x: -x["count"])
        rev = sum(self.reverse_totals.values())
        return {
            "total": sum(self.totals.values()),
            "reverse_total": rev,
            "uncertain": self.uncertain,
            "per_product": per,
            "paused": self.paused,
            "paused_reason": "Train ketmoqda — sanash to'xtatilgan" if self.paused else None,
            "last_event": self.last_event,
            "models": len(self.products),
            "error": self.last_error,
            "dry_run": self.dry_run,
        }

    def close(self) -> None:
        pass
