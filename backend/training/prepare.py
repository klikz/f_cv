"""Bitta mahsulot uchun YOLO formatidagi dataset (PLAN.md 1.6, 1.9).

- Ijobiy: shu mahsulot ramkalari (1 klass, tasdiqlangan);
- Negativ: boshqa mahsulotli va bo'sh rasmlar — **yorliqsiz** (fon), nisbati sozlanadi;
- Kesim: kameraning sanash ROI atrofi (inference bilan bir xil);
- Train/val bo'linishi rasm identifikatori bo'yicha barqaror (qayta train'da o'zgarmaydi).
"""

from __future__ import annotations

import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import cv2
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog import Annotation, DatasetImage, Product
from app.models.tasks import CountingConfig
from app.services.images import mask_outside_roi, roi_crop_box


@dataclass
class DatasetStats:
    positives: int = 0
    negatives: int = 0
    objects: int = 0
    train_images: int = 0
    val_images: int = 0
    per_stream: dict[str, int] = field(default_factory=dict)
    per_camera: dict[int, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def is_val(image_id: int) -> bool:
    return (image_id * 2654435761 % 2**32) % 100 < 20


def crop_boxes(session: Session) -> dict[int, list | None]:
    return {c.camera_id: c.roi_polygon for c in session.execute(select(CountingConfig)).scalars()}


def build_dataset(
    session: Session,
    product_id: int,
    out_dir: Path,
    *,
    camera_id: int | None = None,
    negative_ratio: float = 1.0,
    include_auto: bool = False,
) -> tuple[Path, DatasetStats]:
    data_root = get_settings().data_path
    product = session.get(Product, product_id)
    if product is None:
        raise ValueError("Mahsulot topilmadi")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sp in ("train", "val"):
        (out_dir / "images" / sp).mkdir(parents=True)
        (out_dir / "labels" / sp).mkdir(parents=True)

    statuses = ["confirmed", "auto"] if include_auto else ["confirmed"]
    q = select(DatasetImage).where(DatasetImage.status.in_(statuses) | DatasetImage.is_empty.is_(True))
    if camera_id:
        q = q.where(DatasetImage.camera_id == camera_id)
    images = session.execute(q).scalars().all()
    rois = crop_boxes(session)
    pos, neg = [], []
    for img in images:
        mine = [a for a in img.annotations if a.product_id == product_id and (include_auto or a.status == "confirmed")]
        (pos if mine else neg).append((img, mine))
    st = DatasetStats()
    if not pos:
        raise ValueError("Bu mahsulot uchun tasdiqlangan ramka yo'q — avval rasmlarni belgilang")
    rnd = random.Random(product_id)
    rnd.shuffle(neg)
    neg = neg[: int(len(pos) * negative_ratio) + 1]

    def write(img: DatasetImage, anns: list[Annotation]) -> bool:
        src = data_root / img.file_path
        frame = cv2.imread(str(src))
        if frame is None:
            st.warnings.append(f"Rasm o'qilmadi: {img.file_path}")
            return False
        h, w = frame.shape[:2]
        # ROI bo'yicha kesib saqlangan rasm qayta kesilmaydi
        x1, y1, x2, y2 = (0, 0, w, h) if img.crop else roi_crop_box(rois.get(img.camera_id or -1), w, h)
        crop = frame[y1:y2, x1:x2]
        if not img.crop:  # ROI kesimi bilan olingan snapshot allaqachon niqoblangan
            crop = mask_outside_roi(crop.copy(), rois.get(img.camera_id or -1), (x1, y1, x2, y2), w, h)
        cw, ch = x2 - x1, y2 - y1
        lines = []
        for a in anns:
            ax1, ay1, ax2, ay2 = a.bbox[0] * w, a.bbox[1] * h, a.bbox[2] * w, a.bbox[3] * h
            area = max(1e-6, (ax2 - ax1) * (ay2 - ay1))
            cx1, cy1, cx2, cy2 = max(ax1, x1), max(ay1, y1), min(ax2, x2), min(ay2, y2)
            if cx2 <= cx1 or cy2 <= cy1 or (cx2 - cx1) * (cy2 - cy1) / area < 0.3:
                continue
            bx, by = ((cx1 + cx2) / 2 - x1) / cw, ((cy1 + cy2) / 2 - y1) / ch
            bw, bh = (cx2 - cx1) / cw, (cy2 - cy1) / ch
            lines.append(f"0 {bx:.6f} {by:.6f} {bw:.6f} {bh:.6f}")
        split = "val" if is_val(img.id) else "train"
        name = f"{img.id}.jpg"
        cv2.imwrite(str(out_dir / "images" / split / name), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        (out_dir / "labels" / split / f"{img.id}.txt").write_text("\n".join(lines))
        if split == "val":
            st.val_images += 1
        else:
            st.train_images += 1
        st.objects += len(lines)
        st.per_stream[img.stream] = st.per_stream.get(img.stream, 0) + 1
        st.per_camera[img.camera_id or 0] = st.per_camera.get(img.camera_id or 0, 0) + 1
        return True

    for img, anns in pos:
        if write(img, anns):
            st.positives += 1
    for img, _ in neg:
        if write(img, []):
            st.negatives += 1
    # val'da kamida bitta ijobiy rasm bo'lsin
    if not any((out_dir / "labels" / "val").iterdir()) or not any(
        p.read_text().strip() for p in (out_dir / "labels" / "val").glob("*.txt")
    ):
        for p in list((out_dir / "labels" / "train").glob("*.txt"))[: max(1, st.positives // 5)]:
            if p.read_text().strip():
                shutil.copy(p, out_dir / "labels" / "val" / p.name)
                shutil.copy(
                    out_dir / "images" / "train" / f"{p.stem}.jpg", out_dir / "images" / "val" / f"{p.stem}.jpg"
                )
                st.val_images += 1
    (out_dir / "data.yaml").write_text(
        f"path: {out_dir}\ntrain: images/train\nval: images/val\nnc: 1\nnames: ['{product.code}']\n"
    )
    if st.positives < 30:
        st.warnings.append(f"Ijobiy rasmlar kam ({st.positives}) — aniqlik past bo'lishi mumkin")
    return out_dir / "data.yaml", st
