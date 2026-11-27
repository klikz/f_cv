"""Dataset avto-yig'ish (3.2.4–3.2.5): ROI da harakat bo'lsa har N soniyada snapshot; takrorlar o'tkaziladi."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog import DatasetImage
from app.services.images import dhash, hamming, roi_crop_box, save_jpeg, task_dir

log = logging.getLogger(__name__)


class AutoCollector:
    def __init__(self, logic) -> None:
        self.logic = logic
        self.interval = 10.0
        self.daily_limit = 500
        self.roi = None
        self.next_at = 0.0
        self.prev: np.ndarray | None = None
        self.recent: deque[int] = deque(maxlen=50)

    def configure(self, cfg: dict, roi) -> None:
        self.interval = float(cfg.get("interval_sec", 10))
        self.daily_limit = int(cfg.get("daily_limit", 500))
        self.roi = roi

    def _day_key(self) -> str:
        d = datetime.now(ZoneInfo(get_settings().timezone)).strftime("%Y%m%d")
        return f"fcv:autocollect:{self.logic.camera_id}:{d}"

    def process(self, seq: int, ts: float, frame: np.ndarray) -> None:
        now = time.time()
        if now < self.next_at:
            return
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = roi_crop_box(self.roi, w, h)
        small = cv2.resize(
            cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY), (64, 36), interpolation=cv2.INTER_AREA
        )
        moving = self.prev is not None and float(np.mean(cv2.absdiff(small, self.prev))) > 2.0
        self.prev = small
        if not moving:
            self.next_at = now + 0.5
            return
        r = self.logic.r
        key = self._day_key()
        if int(r.get(key) or 0) >= self.daily_limit:
            self.next_at = now + 60
            return
        hsh = dhash(frame)
        if any(hamming(hsh, x) <= 4 for x in self.recent):
            self.next_at = now + 1.0
            return
        self.recent.append(hsh)
        rel = save_jpeg(frame, task_dir(self.logic.images_root, self.logic.camera_id, "counting") / "dataset")
        with Session(self.logic.engine) as s:
            s.add(
                DatasetImage(
                    camera_id=self.logic.camera_id,
                    stream=self.logic.analysis_kind,
                    file_path=rel,
                    width=w,
                    height=h,
                    source="auto",
                    status="unlabeled",
                    phash=hsh,
                )
            )
            s.commit()
        r.incr(key)
        r.expire(key, 2 * 86400)
        self.next_at = now + self.interval
