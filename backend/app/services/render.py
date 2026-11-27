"""Sanoq snapshotini ramka va nomi bilan chizish (UI va Telegram uchun)."""

import cv2

from app.services.images import abs_path


def render_snapshot(path: str, bbox: list[float] | None, label: str, color=(80, 220, 120)) -> bytes:
    img = cv2.imread(str(abs_path(path)))
    if img is None:
        raise FileNotFoundError(path)
    if bbox:
        h, w = img.shape[:2]
        x1, y1, x2, y2 = int(bbox[0] * w), int(bbox[1] * h), int(bbox[2] * w), int(bbox[3] * h)
        t = max(2, w // 400)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, t)
        fs = max(0.6, w / 1600)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
        cv2.rectangle(img, (x1, max(0, y1 - th - 12)), (x1 + tw + 12, y1), (20, 20, 20), -1)
        cv2.putText(img, label, (x1 + 6, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, fs, color, 2, cv2.LINE_AA)
    _ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()
