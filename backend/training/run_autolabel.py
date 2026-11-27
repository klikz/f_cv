"""Avto-belgilash subprocess'i: stdin'dan JSON (model, rasmlar + kesimlar) → har rasm uchun ramkalar."""

import json
import sys

import cv2

from app.services.images import mask_outside_roi
from training.ml_env import setup_ultralytics_env


def main() -> None:
    req = json.loads(sys.stdin.read())
    setup_ultralytics_env()
    from ultralytics import YOLO

    model = YOLO(req["model"], task="detect")
    conf = float(req.get("conf", 0.25))
    for it in req["images"]:
        img = cv2.imread(it["path"])
        if img is None:
            continue
        h, w = img.shape[:2]
        x1, y1, x2, y2 = it["crop"]
        crop = mask_outside_roi(img[y1:y2, x1:x2].copy(), it.get("roi"), (x1, y1, x2, y2), w, h)
        r = model.predict(crop, imgsz=req.get("imgsz", 640), conf=conf, verbose=False, device=0)[0]
        boxes = []
        for b, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), strict=False):
            bx1, by1, bx2, by2 = b
            boxes.append({"bbox": [(bx1 + x1) / w, (by1 + y1) / h, (bx2 + x1) / w, (by2 + y1) / h], "conf": c})
        print("FCV_PRED " + json.dumps({"id": it["id"], "boxes": boxes}), flush=True)


if __name__ == "__main__":
    main()
