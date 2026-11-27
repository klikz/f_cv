"""Sanash geometriyasi: poligon ichidami, chiziq kesish, yo'nalish (PLAN.md 1.7).

Koordinatalar piksellarda (tahlil oqimi kadri). Chiziq A→B; "oldinga" yo'nalish normali
n = (-dy, dx) — UI'dagi strelka bilan bir xil (A→B ni ekranda soat strelkasi bo'yicha 90° burish).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

Point = tuple[float, float]


def point_in_polygon(p: Point, poly: list[Point]) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def side(a: Point, b: Point, p: Point) -> float:
    """Ishorali masofa (piksel): >0 — normal tomoni ("oldinga" tomon)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / ln, dx / ln
    return (p[0] - a[0]) * nx + (p[1] - a[1]) * ny


def segments_intersect(p1: Point, p2: Point, a: Point, b: Point) -> bool:
    def orient(o: Point, q: Point, r: Point) -> float:
        return (q[0] - o[0]) * (r[1] - o[1]) - (q[1] - o[1]) * (r[0] - o[0])

    d1, d2 = orient(a, b, p1), orient(a, b, p2)
    d3, d4 = orient(p1, p2, a), orient(p1, p2, b)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def angle_to_normal(a: Point, b: Point, v: Point) -> float:
    """Harakat vektori va chiziq normali (ishorasiz) orasidagi burchak, gradus."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / ln, dx / ln
    vl = math.hypot(*v) or 1e-9
    c = abs(v[0] * nx + v[1] * ny) / vl
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def crosses_segment(p1: Point, p2: Point, s1: int, s2: int, a: Point, b: Point) -> bool:
    """Tomon ishorasi o'zgardi (s1 != s2) va kesishuv nuqtasi AB kesmasi ichida."""
    if s1 == s2 or s1 == 0 or s2 == 0:
        return False
    d1, d2 = side(a, b, p1), side(a, b, p2)
    t = d1 / (d1 - d2) if d1 != d2 else 0.5
    ix, iy = p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t
    abx, aby = b[0] - a[0], b[1] - a[1]
    u = ((ix - a[0]) * abx + (iy - a[1]) * aby) / ((abx * abx + aby * aby) or 1e-9)
    return 0.0 <= u <= 1.0


@dataclass
class CrossingState:
    """Bitta track uchun chiziq kesish holati (histerezis bilan)."""

    history: list[Point] = field(default_factory=list)
    max_side_dist: dict[int, float] = field(default_factory=lambda: {1: 0.0, -1: 0.0})
    last_sign: int = 0  # oxirgi nolga teng bo'lmagan tomon
    pending: int | None = None  # kesib o'tdi, lekin yangi tomonda yetarli uzoqlashmagan
    pending_vec: Point | None = None
    counted: bool = False
    counted_dir: int | None = None


@dataclass
class LineCounter:
    a: Point
    b: Point
    max_angle: float = 60.0
    min_track_frames: int = 3
    min_distance: float = 10.0  # piksel

    def update(self, st: CrossingState, p: Point, age: int) -> int | None:
        """Yangi nuqta. Sanoq tasdiqlansa yo'nalishni qaytaradi: +1 (oldinga, A→B strelkasi) yoki -1."""
        prev = st.history[-1] if st.history else None
        st.history.append(p)
        if len(st.history) > 60:
            del st.history[:-60]
        d = side(self.a, self.b, p)
        sgn = 1 if d > 0 else (-1 if d < 0 else st.last_sign)
        prev_sign = st.last_sign
        if sgn != 0:
            st.max_side_dist[sgn] = max(st.max_side_dist[sgn], abs(d))
            st.last_sign = sgn
        if prev is not None and st.pending is None and crosses_segment(prev, p, prev_sign, sgn, self.a, self.b):
            start_side = -sgn
            v = (
                (p[0] - st.history[0][0], p[1] - st.history[0][1])
                if len(st.history) > 2
                else (p[0] - prev[0], p[1] - prev[1])
            )
            # boshlang'ich tomonda yetarli uzoqlikda ko'rilganmi (chiziq yonida tug'ilgan tracklardan himoya)
            if st.max_side_dist[start_side] >= self.min_distance:
                st.pending = sgn
                st.pending_vec = v
        if st.pending is not None:
            if sgn != st.pending:  # orqaga qaytdi (chiziq ustida titrash)
                st.pending = None
                return None
            if abs(d) >= self.min_distance:
                direction = st.pending
                v = st.pending_vec or (0.0, 0.0)
                st.pending = None
                if age < self.min_track_frames:
                    return None
                if angle_to_normal(self.a, self.b, v) > self.max_angle:
                    return None
                if st.counted and st.counted_dir == direction:
                    return None
                    # teskari yo'nalishda qayta kesib o'tish — siyosatga qarab ishlanadi
                st.counted = True
                st.counted_dir = direction
                return direction
        return None


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float32)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter + 1e-9)
