"""Uskuna ish vaqti vazifasi (camera-logic ichida): harakat signali, holat, sikllar. Snapshot saqlanmaydi.

- Xom signal faqat Redis'da (oxirgi ~3 soat, `fcv:signal:<kamera>` stream) — UI grafigi va sozlash uchun;
- PostgreSQL ga: holat intervallari (smena chegarasida bo'linadi), sikl hodisalari, daqiqalik yig'indi.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import keys
from app.models.equipment import CycleEvent, EquipmentInterval, EquipmentMinuteStat
from app.models.tasks import EquipmentConfig
from app.services.images import abs_path, roi_crop_box
from vision.logic.counting import SyncShifts
from vision.motion.signal import (
    HomeCycleDetector,
    MotionMeter,
    PeakCycleDetector,
    ReferenceTracker,
    StateMachine,
    motion_contours,
    polygon_mask,
)

log = logging.getLogger(__name__)

SIGNAL_MAXLEN = 3 * 3600 * 10  # ~3 soat, 10 Hz


def dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, UTC)


class EquipmentTask:
    task_type = "equipment"

    def __init__(self, logic, cfg: EquipmentConfig) -> None:
        self.logic = logic
        self.cam_id = logic.camera_id
        self.r = logic.r
        self.engine = logic.engine
        self.shifts = SyncShifts(self.engine)
        self.meter = MotionMeter()
        self.sm = StateMachine()
        self.home = HomeCycleDetector()
        self.peaks = PeakCycleDetector()
        self.ref = ReferenceTracker()
        self.cfg = cfg
        self.smooth = 0.0
        self.home_diff = 0.0
        self.home_img: np.ndarray | None = None
        self.home_full: np.ndarray | None = None
        self.interval_id: int | None = None
        self.shift_key: tuple | None = None
        self.run_sec = 0.0
        self.stop_sec = 0.0
        self.cycles = 0
        self.micro = 0
        self.last_cycle: float | None = None
        self.cycle_durs: list[float] = []
        self.last_ts: float | None = None
        self.minute: int | None = None
        self.min_acc = [0.0, 0, 0.0]  # harakat yig'indisi, kadrlar, ish soniyalari
        self.contours: list = []
        self.box = (0, 0, 1, 1)
        self.scale = 1.0
        self.masks: tuple | None = None
        self.mask_key: tuple | None = None
        self.idle_candidate_at = 0.0
        self.low_since: float | None = None
        self.reload(cfg)
        self._recover()

    # ---------- konfiguratsiya / tiklanish ----------
    def reload(self, cfg: EquipmentConfig) -> None:
        self.cfg = cfg
        self.sm.threshold, self.sm.min_on, self.sm.min_off = cfg.motion_threshold, cfg.min_on_sec, cfg.min_off_sec
        self.home.exit_thr, self.home.return_thr, self.home.k = (
            cfg.home_exit_threshold,
            cfg.home_return_threshold,
            cfg.returns_per_cycle,
        )
        self.peaks.min_height, self.peaks.min_distance, self.peaks.k = (
            cfg.peak_min_height,
            cfg.peak_min_distance_sec,
            cfg.returns_per_cycle,
        )
        self.ref.auto, self.ref.manual = cfg.auto_reference, cfg.reference_cycle_sec
        self.mask_key = None
        self.home_img = None
        self.home_full = None
        if cfg.home_reference:
            self.home_full = cv2.imread(str(abs_path(cfg.home_reference)), cv2.IMREAD_GRAYSCALE)

    def _recover(self) -> None:
        """Ochiq qolgan intervalni yopish (oxirgi signal vaqtida) va joriy smena ko'rsatkichlarini bazadan tiklash."""
        last = self.r.xrevrange(keys.motion_signal(self.cam_id), count=1)
        last_ts = float(last[0][1]["t"]) if last else None
        with Session(self.engine) as s:
            opened = (
                s.execute(
                    select(EquipmentInterval).where(
                        EquipmentInterval.camera_id == self.cam_id, EquipmentInterval.end_ts.is_(None)
                    )
                )
                .scalars()
                .all()
            )
            for iv in opened:
                end = dt(last_ts) if last_ts and last_ts > iv.start_ts.timestamp() else datetime.now(UTC)
                iv.end_ts = end
            s.commit()
        self._load_shift_totals()

    def _load_shift_totals(self) -> None:
        m = self.shifts.match(datetime.now(UTC))
        self.shift_key = (m.shift_id, m.shift_date) if m else None
        self.run_sec = self.stop_sec = 0.0
        self.cycles = self.micro = 0
        self.cycle_durs = []
        if not m:
            return
        with Session(self.engine) as s:
            ivs = (
                s.execute(
                    select(EquipmentInterval).where(
                        EquipmentInterval.camera_id == self.cam_id,
                        EquipmentInterval.shift_id == m.shift_id,
                        EquipmentInterval.shift_date == m.shift_date,
                    )
                )
                .scalars()
                .all()
            )
            for iv in ivs:
                end = iv.end_ts or datetime.now(UTC)
                d = (end - iv.start_ts).total_seconds()
                if iv.state == "running":
                    self.run_sec += d
                elif iv.state == "stopped":
                    self.stop_sec += d
            cyc = s.execute(
                select(CycleEvent.duration, CycleEvent.is_micro_stop)
                .where(
                    CycleEvent.camera_id == self.cam_id,
                    CycleEvent.shift_id == m.shift_id,
                    CycleEvent.shift_date == m.shift_date,
                )
                .order_by(CycleEvent.end_ts)
            ).all()
        self.cycles = len(cyc)
        self.micro = sum(1 for _, ms in cyc if ms)
        self.cycle_durs = [d for d, _ in cyc][-200:]
        if self.cycle_durs:
            self.last_cycle = self.cycle_durs[-1]
            for d in self.cycle_durs[:10]:
                self.ref.add(d)

    # ---------- intervallar ----------
    def _open_interval(self, state: str, start: float) -> None:
        m = self.shifts.match(dt(start))
        with Session(self.engine) as s:
            if self.interval_id:
                s.execute(
                    update(EquipmentInterval).where(EquipmentInterval.id == self.interval_id).values(end_ts=dt(start))
                )
            iv = EquipmentInterval(
                camera_id=self.cam_id,
                state=state,
                start_ts=dt(start),
                shift_id=m.shift_id if m else None,
                shift_date=m.shift_date if m else None,
            )
            s.add(iv)
            s.commit()
            self.interval_id = iv.id

    def _emit_state(self, state: str, since: float) -> None:
        payload = json.dumps(
            {"kind": "equipment_state", "ts": time.time(), "camera_id": self.cam_id, "state": state, "since": since},
            ensure_ascii=False,
        )
        with self.r.pipeline(transaction=False) as p:
            p.publish(keys.CH_EVENTS, payload)
            p.xadd(keys.STREAM_EVENTS, {"data": payload}, maxlen=100_000, approximate=True)
            p.execute()

    # ---------- kadr ----------
    def _prepare_masks(self, w: int, h: int) -> None:
        key = (
            w,
            h,
            json.dumps(self.cfg.roi_polygon),
            json.dumps(self.cfg.control_zone),
            json.dumps(self.cfg.exclude_zones),
        )
        if key == self.mask_key:
            return
        polys = [self.cfg.roi_polygon] + ([self.cfg.control_zone] if self.cfg.control_zone else [])
        allpts = [p for poly in polys for p in poly]
        self.box = roi_crop_box(allpts, w, h, margin=0.02, min_size=16)
        bw = self.box[2] - self.box[0]
        self.scale = min(1.0, 160.0 / max(1, bw))
        sh = (max(1, int((self.box[3] - self.box[1]) * self.scale)), max(1, int(bw * self.scale)))
        px = lambda poly: [(x * w, y * h) for x, y in poly]  # noqa: E731
        roi_m = polygon_mask(sh, px(self.cfg.roi_polygon), self.box, self.scale)
        for z in self.cfg.exclude_zones or []:
            zm = polygon_mask(sh, px(z), self.box, self.scale)
            if roi_m is not None and zm is not None:
                roi_m = cv2.bitwise_and(roi_m, cv2.bitwise_not(zm))
        ctrl = polygon_mask(sh, px(self.cfg.control_zone), self.box, self.scale) if self.cfg.control_zone else None
        self.masks = (roi_m, ctrl, sh)
        self.mask_key = key
        self.meter.reset()
        # tayanch kadr — xuddi shu ROI kesimi va o'lchamda
        self.home_img = None
        if self.home_full is not None:
            fh, fw = self.home_full.shape[:2]
            sx, sy = fw / w, fh / h
            bx1, by1, bx2, by2 = (
                int(self.box[0] * sx),
                int(self.box[1] * sy),
                int(self.box[2] * sx),
                int(self.box[3] * sy),
            )
            self.home_img = cv2.resize(self.home_full[by1:by2, bx1:bx2], (sh[1], sh[0]), interpolation=cv2.INTER_AREA)

    def process(self, seq: int, ts: float, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        self._prepare_masks(w, h)
        roi_m, ctrl, sh = self.masks  # type: ignore[misc]
        x1, y1, x2, y2 = self.box
        g = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (sh[1], sh[0]), interpolation=cv2.INTER_AREA)
        pct, cpct = self.meter.measure(g, roi_m, ctrl)
        corrected = max(0.0, pct - cpct)  # nazorat zonasi: kamera titrashi ayiriladi
        self.smooth = 0.6 * self.smooth + 0.4 * corrected
        # tayanch holatdan farq
        if self.home_img is not None:
            ref = self.home_img
            d = cv2.absdiff(cv2.GaussianBlur(g, (5, 5), 0), cv2.GaussianBlur(ref, (5, 5), 0))
            self.home_diff = (
                float(np.mean(d[roi_m > 0]) / 255.0 * 100.0 * 4) if roi_m is not None else float(np.mean(d) / 2.55)
            )
            # yorug'lik o'zgarishiga moslashish: tayanchda va tinch paytda sekin yangilash
            if self.home.at_home and self.smooth < self.cfg.motion_threshold * 0.5:
                self.home_img = cv2.addWeighted(ref, 0.995, g, 0.005, 0)
        prev_state = self.sm.state
        changed = self.sm.update(self.smooth, ts)
        if changed:
            self._open_interval(changed, self.sm.since)
            if prev_state != "unknown" or changed == "running":
                self._emit_state(changed, self.sm.since)
        # vaqt hisobi
        if self.last_ts is not None:
            dtm = min(1.0, ts - self.last_ts)
            if self.sm.state == "running":
                self.run_sec += dtm
            elif self.sm.state == "stopped":
                self.stop_sec += dtm
            self._minute_acc(ts, self.smooth, dtm if self.sm.state == "running" else 0.0)
        self.last_ts = ts
        # sikllar
        cyc = None
        if self.cfg.cycle_mode == "home" and self.home_img is not None:
            cyc = self.home.update(self.home_diff, ts)
        elif self.cfg.cycle_mode == "peaks":
            cyc = self.peaks.update(self.smooth, ts)
        if cyc:
            self._record_cycle(*cyc)
        # tinch holat kadri (tayanch taklifi uchun)
        if self.smooth < self.cfg.motion_threshold * 0.3:
            self.low_since = self.low_since or ts
            if ts - self.low_since > 1.0 and ts - self.idle_candidate_at > 30:
                self.idle_candidate_at = ts
                self._save_candidate(frame)
        else:
            self.low_since = None
        self.contours = motion_contours(self.meter.last_mask, self.box, self.scale, (w, h))
        self.r.xadd(
            keys.motion_signal(self.cam_id),
            {"t": f"{ts:.2f}", "m": f"{self.smooth:.2f}", "h": f"{self.home_diff:.2f}", "s": self.sm.state[0]},
            maxlen=SIGNAL_MAXLEN,
            approximate=True,
        )

    def _save_candidate(self, frame: np.ndarray) -> None:
        from app.core.files import atomic_write_bytes
        from app.services.images import task_dir

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if ok:
            atomic_write_bytes(
                task_dir(self.logic.images_root, self.cam_id, "equipment") / "home_candidate.jpg", buf.tobytes()
            )

    def _record_cycle(self, start: float, end: float) -> None:
        # to'liq davr: oldingi sikl tugashidan shu sikl tugashigacha (uskuna to'xtamagan bo'lsa)
        prev = getattr(self, "prev_cycle_end", None)
        self.prev_cycle_end = end
        if prev is not None and self.sm.state == "running" and end - prev < 600:
            start = prev
        dur = end - start
        if dur <= 0.2:
            return
        ref = self.ref.value
        self.ref.add(dur)
        micro = bool(ref and dur > ref * float(self.cfg.micro_stop_factor))
        self.cycles += 1
        self.micro += int(micro)
        self.last_cycle = dur
        self.cycle_durs.append(dur)
        self.cycle_durs = self.cycle_durs[-200:]
        m = self.shifts.match(dt(end))
        with Session(self.engine) as s:
            s.add(
                CycleEvent(
                    camera_id=self.cam_id,
                    start_ts=dt(start),
                    end_ts=dt(end),
                    duration=round(dur, 3),
                    deviation=round(dur - ref, 3) if ref else None,
                    is_micro_stop=micro,
                    shift_id=m.shift_id if m else None,
                    shift_date=m.shift_date if m else None,
                )
            )
            s.commit()

    def _minute_acc(self, ts: float, motion: float, run_dt: float) -> None:
        minute = int(ts // 60)
        if self.minute is None:
            self.minute = minute
        if minute != self.minute:
            s_, n, run = self.min_acc
            if n:
                with Session(self.engine) as s:
                    s.merge(
                        EquipmentMinuteStat(
                            camera_id=self.cam_id,
                            minute=dt(self.minute * 60),
                            avg_motion=round(s_ / n, 3),
                            run_seconds=round(min(60.0, run), 2),
                        )
                    )
                    s.commit()
            self.minute = minute
            self.min_acc = [0.0, 0, 0.0]
        self.min_acc[0] += motion
        self.min_acc[1] += 1
        self.min_acc[2] += run_dt

    def tick(self, now: float) -> None:
        m = self.shifts.match(dt(now))
        key = (m.shift_id, m.shift_date) if m else None
        if key != self.shift_key:
            # smena almashdi: ochiq intervalni chegarada bo'lish, hisoblagichlar noldan
            if self.interval_id and self.sm.state in ("running", "stopped"):
                self._open_interval(self.sm.state, now)
            self._load_shift_totals()

    def on_stream_lost(self) -> None:
        now = time.time()
        if self.sm.set_unknown(now):
            self._open_interval("unknown", now)
            self.meter.reset()
            self.last_ts = None

    def overlay(self) -> dict[str, Any]:
        return {
            "roi": self.cfg.roi_polygon,
            "control_zone": self.cfg.control_zone,
            "exclude_zones": self.cfg.exclude_zones or [],
            "state": self.sm.state,
            "motion": self.contours,
            "motion_pct": round(self.smooth, 2),
        }

    def live(self) -> dict[str, Any]:
        total = self.run_sec + self.stop_sec
        avg = float(np.mean(self.cycle_durs[-50:])) if self.cycle_durs else None
        return {
            "state": self.sm.state,
            "state_since": self.sm.since or None,
            "run_seconds": round(self.run_sec, 1),
            "stop_seconds": round(self.stop_sec, 1),
            "cycles": self.cycles,
            "last_cycle_sec": round(self.last_cycle, 2) if self.last_cycle else None,
            "avg_cycle_sec": round(avg, 2) if avg else None,
            "reference_cycle_sec": round(self.ref.value, 2) if self.ref.value else None,
            "utilization_pct": round(self.run_sec / total * 100, 1) if total > 0 else None,
            "motion_pct": round(self.smooth, 2),
            "home_diff": round(self.home_diff, 2),
            "micro_stops": self.micro,
            "has_home": self.home_img is not None,
        }

    def close(self) -> None:
        if self.interval_id:
            with Session(self.engine) as s:
                s.execute(
                    update(EquipmentInterval)
                    .where(EquipmentInterval.id == self.interval_id)
                    .values(end_ts=datetime.now(UTC))
                )
                s.commit()
