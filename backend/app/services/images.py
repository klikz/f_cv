"""Rasm yordamchilari: vazifa papkalari, JPEG saqlash (atomar), dHash (takror kadrlarni aniqlash), ROI kesimi."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.files import atomic_write_bytes


def dhash(img: np.ndarray) -> int:
    """64 bitli farq-xesh: deyarli bir xil kadrlar uchun Hamming masofasi kichik."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (s[:, 1:] > s[:, :-1]).flatten()
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v - (1 << 64) if v >= (1 << 63) else v  # PostgreSQL BIGINT uchun ishorali


def hamming(a: int, b: int) -> int:
    return bin((a ^ b) & ((1 << 64) - 1)).count("1")


IMAGES_ROOT_KEY = "storage.images_root"
DEFAULT_IMAGES_SUBDIR = "images"


def resolve_images_root(value: str | None) -> Path:
    """Vazifa rasmlari umumiy papkasi: bo'sh — data/images; nisbiy — data/ ga nisbatan; mutlaq — o'zi."""
    data = get_settings().data_path
    v = (value or "").strip()
    if not v:
        return data / DEFAULT_IMAGES_SUBDIR
    p = Path(v).expanduser()
    return p if p.is_absolute() else data / p


async def images_root(session) -> Path:
    from app.services.settings_store import get_setting

    return resolve_images_root(await get_setting(session, IMAGES_ROOT_KEY))


def task_dir(root: Path, camera_id: int | None, task_type: str) -> Path:
    """Har bir vazifaning alohida papkasi: <umumiy>/cam<kamera>-<vazifa>."""
    return root / f"cam{camera_id or 0}-{task_type}"


def to_stored(path: Path) -> str:
    """Bazaga yoziladigan yo'l: data/ ichida bo'lsa — nisbiy, aks holda — mutlaq."""
    try:
        return str(path.relative_to(get_settings().data_path))
    except ValueError:
        return str(path)


def save_jpeg(img: np.ndarray, folder: Path, quality: int = 92) -> str:
    """<folder>/<sana>/<uuid>.jpg — bazaga yoziladigan yo'lni qaytaradi (`to_stored`)."""
    day = datetime.now(ZoneInfo(get_settings().timezone)).strftime("%Y-%m-%d")
    path = folder / day / f"{uuid4().hex}.jpg"
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG kodlab bo'lmadi")
    atomic_write_bytes(path, buf.tobytes())
    return to_stored(path)


def abs_path(rel: str) -> Path:
    """Bazadagi yo'l → mutlaq. Mutlaq yo'llarni faqat server o'zi yozadi (tashqi rasmlar papkasi)."""
    if Path(rel).is_absolute():
        return Path(rel).resolve()
    p = (get_settings().data_path / rel).resolve()
    if not p.is_relative_to(get_settings().data_path.resolve()):
        raise ValueError("Ruxsat etilmagan yo'l")
    return p


ROI_FILL = (114, 114, 114)  # ROI tashqarisi — YOLO letterbox rangi (model uchun "bo'sh joy")


def roi_crop_box(
    roi: list | None, w: int, h: int, margin: float = 0.0, min_size: int = 64
) -> tuple[int, int, int, int]:
    """ROI poligonining chegara to'rtburchagi, piksel. ROI yo'q bo'lsa — butun kadr.

    Train va inference bir xil kesimdan foydalanadi (PLAN.md 1.6: kirish — ROI kesimi, tashqarisi
    `mask_outside_roi` bilan bo'yalgan).
    """
    if not roi:
        return 0, 0, w, h
    xs = [p[0] for p in roi]
    ys = [p[1] for p in roi]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    x1, y1 = max(0.0, x1 - mx), max(0.0, y1 - my)
    x2, y2 = min(1.0, x2 + mx), min(1.0, y2 + my)
    bx1, by1, bx2, by2 = int(x1 * w), int(y1 * h), round(x2 * w), round(y2 * h)
    if bx2 - bx1 < min_size or by2 - by1 < min_size:
        return 0, 0, w, h
    return bx1, by1, bx2, by2


def mask_outside_roi(img: np.ndarray, roi: list | None, box: tuple[int, int, int, int] | list[int], w: int, h: int):
    """`img` — (w×h) kadrning `box` kesimi. ROI poligonidan tashqari piksellar ROI_FILL bilan bo'yaladi (joyida)."""
    if not roi or len(roi) < 3:
        return img
    x1, y1 = box[0], box[1]
    pts = np.array([[p[0] * w - x1, p[1] * h - y1] for p in roi], dtype=np.float64)
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 255)
    img[mask == 0] = ROI_FILL
    return img
