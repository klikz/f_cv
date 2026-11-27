"""Harakat signali va sikl detektorlari (sof hisob — test qilish oson, PLAN.md 1.8)."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


def polygon_mask(
    shape: tuple[int, int], poly: list | None, box: tuple[int, int, int, int], scale: float
) -> np.ndarray | None:
    """Kesim (box) ichidagi kichraytirilgan maska: poligon (0–1 kadr koordinatalari) → 255."""
    if not poly:
        return None
    h, w = shape
    x1, y1, _, _ = box
    m = np.zeros((h, w), np.uint8)
    pts = np.array([[(px - x1) * scale, (py - y1) * scale] for px, py in poly], dtype=np.int32)
    cv2.fillPoly(m, [pts], 255)
    return m


class MotionMeter:
    """ROI kesimi → kulrang → kichraytirish → kadrlar farqi + MOG2 → harakat foizi (ROI maydoniga nisbatan)."""

    def __init__(self, width: int = 160, diff_thr: int = 18) -> None:
        self.width = width
        self.diff_thr = diff_thr
        self.prev: np.ndarray | None = None
        self.mog = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=24, detectShadows=False)
        self.last_mask: np.ndarray | None = None

    def reset(self) -> None:
        self.prev = None
        self.mog = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=24, detectShadows=False)

    def measure(
        self, gray_small: np.ndarray, roi_mask: np.ndarray | None, control_mask: np.ndarray | None = None
    ) -> tuple[float, float]:
        """(harakat %, nazorat zonasi harakati %)."""
        g = cv2.GaussianBlur(gray_small, (3, 3), 0)
        if self.prev is None or self.prev.shape != g.shape:
            self.prev = g
            self.mog.apply(g, learningRate=0.5)
            return 0.0, 0.0
        diff = (cv2.absdiff(g, self.prev) > self.diff_thr).astype(np.uint8) * 255
        fg = self.mog.apply(g, learningRate=0.01)
        self.prev = g
        motion = cv2.bitwise_or(diff, cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)))
        self.last_mask = motion if roi_mask is None else cv2.bitwise_and(motion, roi_mask)
        area = float(np.count_nonzero(roi_mask)) if roi_mask is not None else float(motion.size)
        pct = float(np.count_nonzero(self.last_mask)) / max(1.0, area) * 100.0
        cpct = 0.0
        if control_mask is not None:
            carea = float(np.count_nonzero(control_mask))
            cpct = float(np.count_nonzero(cv2.bitwise_and(diff, control_mask))) / max(1.0, carea) * 100.0
        return pct, cpct


def motion_contours(
    mask: np.ndarray | None,
    box: tuple[int, int, int, int],
    scale: float,
    frame_wh: tuple[int, int],
    max_items: int = 12,
) -> list[list[list[float]]]:
    """Harakat maskasidan soddalashtirilgan konturlar (0–1 kadr koordinatalari) — AI qatlami uchun."""
    if mask is None:
        return []
    m = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:max_items]
    w, h = frame_wh
    x1, y1 = box[0], box[1]
    out = []
    for c in cnts:
        if cv2.contourArea(c) < 12:
            continue
        c = cv2.approxPolyDP(c, 1.5, True)
        if len(c) < 3:
            continue
        out.append(
            [[round((x1 + float(p[0][0]) / scale) / w, 4), round((y1 + float(p[0][1]) / scale) / h, 4)] for p in c]
        )
    return out


@dataclass
class StateMachine:
    """ISHLAYAPTI ⇄ TO'XTAGAN (debounce: min_on / min_off); kamera uzilsa — NOMA'LUM.

    Nomzod holat qisqa qaytishlarda bekor bo'lmaydi: masalan press har siklda ~1 s tayanchda turadi —
    "ishlayapti" nomzodi bu tanaffuslardan (≤ grace) uzilmaydi.
    """

    threshold: float = 2.0
    min_on: float = 3.0
    min_off: float = 10.0
    state: str = "unknown"
    since: float = 0.0
    _cand: str | None = None
    _cand_since: float = 0.0
    _cand_last: float = 0.0

    def _grace(self, cand: str) -> float:
        return min(self.min_off, 2.0) if cand == "running" else min(self.min_on, 1.0)

    def update(self, pct: float, ts: float) -> str | None:
        """Holat o'zgarsa yangi holatni qaytaradi (o'zgarish vaqti — since)."""
        obs = "running" if pct >= self.threshold else "stopped"
        if self.state == "unknown":
            if self._cand != obs:
                self._cand, self._cand_since = obs, ts
            if ts - self._cand_since >= 1.0:
                self.state, self.since, self._cand = obs, self._cand_since, None
                return obs
            return None
        if obs != self.state:
            if self._cand != obs:
                self._cand, self._cand_since = obs, ts
            self._cand_last = ts
        elif self._cand is not None and ts - self._cand_last > self._grace(self._cand):
            self._cand = None
        if self._cand is not None:
            need = self.min_on if self._cand == "running" else self.min_off
            if ts - self._cand_since >= need:
                self.state, self.since, self._cand = self._cand, self._cand_since, None
                return self.state
        return None

    def set_unknown(self, ts: float) -> bool:
        if self.state == "unknown":
            return False
        self.state, self.since, self._cand = "unknown", ts, None
        return True


@dataclass
class HomeCycleDetector:
    """Tayanch holat bo'yicha: signal = tayanch ko'rinishdan farq; sikl = tayanchga K marta qaytish."""

    exit_thr: float = 12.0
    return_thr: float = 6.0
    k: int = 1
    at_home: bool = True
    returns: int = 0
    cycle_start: float | None = None
    left_at: float | None = None

    def update(self, diff: float, ts: float) -> tuple[float, float] | None:
        """Sikl tugasa (boshlanish, tugash) qaytaradi."""
        if self.at_home and diff >= self.exit_thr:
            self.at_home = False
            self.left_at = ts
            if self.cycle_start is None:
                self.cycle_start = ts
        elif not self.at_home and diff <= self.return_thr:
            self.at_home = True
            self.returns += 1
            if self.returns >= self.k and self.cycle_start is not None:
                start = self.cycle_start
                self.returns = 0
                self.cycle_start = None
                return start, ts
        return None


@dataclass
class PeakCycleDetector:
    """Harakat cho'qqilari bo'yicha: cho'qqi = signal min_height dan oshib, yarmigacha tushganda; sikl = K cho'qqi."""

    min_height: float = 5.0
    min_distance: float = 0.5
    k: int = 1
    _peak: float = 0.0
    _peak_ts: float = 0.0
    _in_peak: bool = False
    _last_peak: float = -1e9
    peaks: int = 0
    cycle_start: float | None = None

    def update(self, v: float, ts: float) -> tuple[float, float] | None:
        if not self._in_peak:
            if v >= self.min_height:
                self._in_peak, self._peak, self._peak_ts = True, v, ts
            return None
        if v > self._peak:
            self._peak, self._peak_ts = v, ts
        if v <= self._peak * 0.5:
            self._in_peak = False
            if self._peak_ts - self._last_peak < self.min_distance:
                return None
            self._last_peak = self._peak_ts
            if self.cycle_start is None:
                self.cycle_start = self._peak_ts
                self.peaks = 0
                return None
            self.peaks += 1
            if self.peaks >= self.k:
                start, end = self.cycle_start, self._peak_ts
                self.cycle_start = end
                self.peaks = 0
                return start, end
        return None


def autocorr_period(signal: np.ndarray, fps: float, min_sec: float = 0.4, max_sec: float = 120.0) -> float | None:
    """Avtokorrelyatsiya bo'yicha asosiy davr (soniya)."""
    x = np.asarray(signal, dtype=np.float64)
    if len(x) < fps * 4:
        return None
    x = x - x.mean()
    if np.allclose(x, 0):
        return None
    n = len(x)
    f = np.fft.rfft(x, n=2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac /= ac[0] or 1.0
    lo, hi = int(min_sec * fps), min(int(max_sec * fps), n // 2)
    if hi <= lo + 2:
        return None
    seg = ac[lo:hi]
    # birinchi aniq cho'qqi (ac > 0.3)
    for i in range(1, len(seg) - 1):
        if seg[i] > 0.3 and seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]:
            return (lo + i) / fps
    i = int(np.argmax(seg))
    return (lo + i) / fps if seg[i] > 0.15 else None


@dataclass
class ReferenceTracker:
    """Etalon sikl vaqti: dastlabki N sikl medianasi (avto) yoki qo'lda kiritilgan qiymat."""

    manual: float | None = None
    auto: bool = True
    n: int = 10
    samples: list[float] = field(default_factory=list)

    def add(self, dur: float) -> None:
        self.samples.append(dur)
        if len(self.samples) > 200:
            self.samples = self.samples[-200:]

    @property
    def value(self) -> float | None:
        if not self.auto and self.manual:
            return self.manual
        if self.manual and len(self.samples) < self.n:
            return self.manual
        if len(self.samples) >= min(self.n, 3):
            return float(np.median(self.samples[: self.n]))
        return None
