"""Yengil ByteTrack (numpy + scipy): Kalman (doimiy tezlik) + ikki bosqichli IoU moslashtirish.

Har kamera camera-logic processida alohida holat. torch talab qilinmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from vision.logic.geometry import iou_matrix


class KalmanBox:
    """Holat: [cx, cy, w, h, vx, vy, vw, vh]."""

    def __init__(self, box: np.ndarray) -> None:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        w, h = box[2] - box[0], box[3] - box[1]
        self.x = np.array([cx, cy, w, h, 0, 0, 0, 0], dtype=np.float64)
        self.P = np.diag([w, h, w, h, w * 2, h * 2, w, h]).astype(np.float64) ** 2 * 0.05
        self.F = np.eye(8)
        for i in range(4):
            self.F[i, i + 4] = 1.0
        self.H = np.eye(4, 8)

    def predict(self) -> np.ndarray:
        w, h = max(self.x[2], 1), max(self.x[3], 1)
        q = np.array([w, h, w, h, w * 0.5, h * 0.5, w * 0.1, h * 0.1]) ** 2 * 0.01
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + np.diag(q)
        return self.box

    def update(self, box: np.ndarray) -> None:
        z = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[2] - box[0], box[3] - box[1]])
        w, h = max(z[2], 1), max(z[3], 1)
        r = np.diag([w, h, w, h]) ** 2 * 0.005
        y = z - self.H @ self.x
        s = self.H @ self.P @ self.H.T + r
        k = self.P @ self.H.T @ np.linalg.inv(s)
        self.x = self.x + k @ y
        self.P = (np.eye(8) - k @ self.H) @ self.P

    @property
    def box(self) -> np.ndarray:
        cx, cy, w, h = self.x[:4]
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])


@dataclass
class Track:
    id: int
    kf: KalmanBox
    box: np.ndarray
    score: float
    age: int = 1  # yangilangan kadrlar soni
    lost: int = 0
    meta: dict = field(default_factory=dict)  # sanash uchun (mahsulot ballari, kesish holati)


class ByteTracker:
    def __init__(
        self, high: float = 0.5, low: float = 0.15, new_track: float = 0.55, match_iou: float = 0.2, max_lost: int = 15
    ) -> None:
        self.high, self.low, self.new_track, self.match_iou, self.max_lost = high, low, new_track, match_iou, max_lost
        self.tracks: list[Track] = []
        self._next = 1

    def reset(self) -> None:
        self.tracks = []

    def _match(self, tracks: list[Track], dets: np.ndarray) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        if not tracks or len(dets) == 0:
            return [], list(range(len(tracks))), list(range(len(dets)))
        tb = np.array([t.box for t in tracks])
        iou = iou_matrix(tb, dets[:, :4])
        r, c = linear_sum_assignment(1 - iou)
        pairs, ut, ud = [], set(range(len(tracks))), set(range(len(dets)))
        for i, j in zip(r, c, strict=True):
            if iou[i, j] >= self.match_iou:
                pairs.append((i, j))
                ut.discard(i)
                ud.discard(j)
        return pairs, sorted(ut), sorted(ud)

    def update(
        self, dets: np.ndarray, det_meta: list[dict] | None = None
    ) -> tuple[list[Track], list[tuple[Track, int]]]:
        """dets: [N, 5] (x1, y1, x2, y2, score). Qaytaradi: faol tracklar va (track, det_index) juftliklari."""
        det_meta = det_meta or [{} for _ in range(len(dets))]
        for t in self.tracks:
            t.box = t.kf.predict()
        hi = np.where(dets[:, 4] >= self.high)[0] if len(dets) else np.array([], dtype=int)
        lo = np.where((dets[:, 4] >= self.low) & (dets[:, 4] < self.high))[0] if len(dets) else np.array([], dtype=int)
        matched: list[tuple[Track, int]] = []
        pairs, ut, ud = self._match(self.tracks, dets[hi] if len(hi) else np.zeros((0, 5)))
        for i, j in pairs:
            matched.append((self.tracks[i], int(hi[j])))
        rem = [self.tracks[i] for i in ut]
        pairs2, _ut2, _ = self._match(rem, dets[lo] if len(lo) else np.zeros((0, 5)))
        for i, j in pairs2:
            matched.append((rem[i], int(lo[j])))
        for t, di in matched:
            t.kf.update(dets[di, :4])
            t.box = t.kf.box
            t.score = float(dets[di, 4])
            t.age += 1
            t.lost = 0
        matched_ids = {id(t) for t, _ in matched}
        for t in self.tracks:
            if id(t) not in matched_ids:
                t.lost += 1
        for j in ud:
            di = int(hi[j])
            if dets[di, 4] >= self.new_track:
                t = Track(self._next, KalmanBox(dets[di, :4]), dets[di, :4].copy(), float(dets[di, 4]))
                self._next += 1
                self.tracks.append(t)
                matched.append((t, di))
        self.tracks = [t for t in self.tracks if t.lost <= self.max_lost]
        return [t for t in self.tracks if t.lost == 0], matched
