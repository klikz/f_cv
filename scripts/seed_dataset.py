"""Sinov uchun belgilangan dataset: soxta konveyer videosidan kadrlar + aniq ramkalar.

Foydalanuvchining belgilash ishini simulyatsiya qiladi (train → engine → sanash zanjirini sinash uchun).
  cd backend && uv run python ../scripts/seed_dataset.py --camera-id 1 --step 0.4
"""

import argparse
import sys
from pathlib import Path

import av
import cv2
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_cameras import BELT_BOTTOM, OUT, PRODUCTS, SPEED, H, W, conveyor_schedule  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.models.catalog import Annotation, DatasetImage, Product  # noqa: E402
from app.services.images import dhash, resolve_images_root, save_jpeg, task_dir  # noqa: E402


def boxes_at(t: float, items):
    out = []
    for i, it in enumerate(items):
        x = it.x0 + (t - it.t0) * SPEED
        if t < it.t0:
            continue
        x1, x2 = x, x + it.w
        y2 = BELT_BOTTOM - 40
        y1 = y2 - it.h
        vx1, vx2 = max(0, x1), min(W, x2)
        if vx2 - vx1 < it.w * 0.35:  # kadrda kam ko'rinadi
            continue
        touching = False
        for j, o in enumerate(items):
            if j == i or t < o.t0:
                continue
            ox = o.x0 + (t - o.t0) * SPEED
            if abs(ox - x2) < 12 or abs(ox + o.w - x1) < 12:
                touching = True
        out.append((it.code, it.boxed, [vx1 / W, y1 / H, vx2 / W, y2 / H], touching))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera-id", type=int, required=True)
    ap.add_argument("--step", type=float, default=0.4)
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args()
    s = get_settings()
    eng = create_engine(s.database_url.replace("+asyncpg", "+psycopg"))
    items = conveyor_schedule(42, 75.0)
    with Session(eng) as ses:
        pids = {}
        for code, (name, _, _) in PRODUCTS.items():
            p = ses.execute(select(Product).where(Product.code == code)).scalar_one_or_none()
            if p is None:
                p = Product(code=code, name=name, category="Maishiy texnika")
                ses.add(p)
                ses.flush()
            pids[code] = p.id
        ses.commit()
        c = av.open(str(OUT / "conveyor_main_h264.mp4"))
        vs = c.streams.video[0]
        next_t, n, n_obj = 0.0, 0, 0
        for fr in c.decode(vs):
            t = float(fr.pts * vs.time_base)
            if t < next_t:
                continue
            next_t = t + a.step
            img = fr.to_ndarray(format="bgr24")
            bxs = boxes_at(t, items)
            rel = save_jpeg(img, task_dir(resolve_images_root(None), a.camera_id, "counting") / "dataset")
            di = DatasetImage(camera_id=a.camera_id, stream="main", file_path=rel, width=img.shape[1], height=img.shape[0],
                              source="manual", status="confirmed", is_empty=not bxs, phash=dhash(img))
            ses.add(di)
            ses.flush()
            for code, boxed, bb, touching in bxs:
                ses.add(Annotation(image_id=di.id, product_id=pids[code], bbox=[round(v, 5) for v in bb],
                                   packaging="boxed" if boxed else "unboxed", status="confirmed", touching=touching))
                n_obj += 1
            n += 1
            if n >= a.max:
                break
        ses.commit()
    print(f"{n} ta rasm, {n_obj} ta ramka qo'shildi (kamera {a.camera_id})")
    _ = cv2


if __name__ == "__main__":
    main()
