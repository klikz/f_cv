"""Dataset: snapshot, rasmlar, belgilash, tayyorlik indikatori, avto-yig'ish."""

from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, delete, exists, func, or_, select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core.config import get_settings
from app.models.cameras import Camera
from app.models.catalog import Annotation, DatasetImage, Product
from app.models.tasks import CountingConfig, EquipmentConfig
from app.services.images import abs_path, dhash, hamming, images_root, roi_crop_box, save_jpeg, task_dir
from app.services.settings_store import get_setting, set_setting
from app.services.snapshot import grab_live_frame

router = APIRouter(prefix="/dataset", tags=["dataset"])


class AnnotationIO(BaseModel):
    id: int | None = None
    product_id: int
    bbox: tuple[float, float, float, float]
    packaging: Literal["boxed", "unboxed"] = "unboxed"
    status: Literal["auto", "confirmed"] = "confirmed"
    confidence: float | None = None
    touching: bool = False


class ImageOut(BaseModel):
    id: int
    camera_id: int | None
    camera_name: str | None = None
    product_id: int | None = None
    stream: str
    crop: list[float] | None = None
    width: int
    height: int
    source: str
    status: str
    is_empty: bool
    captured_at: datetime
    annotations: list[AnnotationIO] = []


class ImageDetail(ImageOut):
    prev_id: int | None = None
    next_id: int | None = None
    position: int | None = None
    total: int | None = None


class ImagesPage(BaseModel):
    items: list[ImageOut]
    total: int
    counts: dict[str, int]


class AnnotationsIn(BaseModel):
    annotations: list[AnnotationIO]
    is_empty: bool = False


class SnapshotIn(BaseModel):
    camera_id: int
    product_id: int | None = None
    mode: Literal["full", "roi"] = "full"


class BulkDeleteIn(BaseModel):
    ids: list[int] | None = None
    # ids berilmasa — filtr bo'yicha (hech biri berilmasa rad etiladi)
    camera_id: int | None = None
    product_id: int | None = None
    source: Literal["manual", "auto", "count"] | None = None


class AutoCollectIn(BaseModel):
    enabled: bool
    interval_sec: float = Field(10, ge=1, le=3600)
    daily_limit: int = Field(500, ge=1, le=100000)


def _filtered(
    camera_id: int | None, product_id: int | None, status: str | None, day: date | None, source: str | None
) -> Select:
    stmt = select(DatasetImage)
    if camera_id:
        stmt = stmt.where(DatasetImage.camera_id == camera_id)
    if status == "empty":
        stmt = stmt.where(DatasetImage.is_empty.is_(True))
    elif status:
        stmt = stmt.where(DatasetImage.status == status)
    if source:
        stmt = stmt.where(DatasetImage.source == source)
    if product_id:
        # shu mahsulot uchun olingan yoki shu mahsulot belgilangan rasmlar
        stmt = stmt.where(
            or_(
                DatasetImage.product_id == product_id,
                exists().where(and_(Annotation.image_id == DatasetImage.id, Annotation.product_id == product_id)),
            )
        )
    if day:
        tz = ZoneInfo(get_settings().timezone)
        start = datetime.combine(day, datetime.min.time(), tz)
        stmt = stmt.where(DatasetImage.captured_at >= start, DatasetImage.captured_at < start + timedelta(days=1))
    return stmt


async def _cam_names(session) -> dict[int, str]:
    return dict((await session.execute(select(Camera.id, Camera.name))).all())


def _img_out(img: DatasetImage, names: dict[int, str]) -> dict:
    return dict(
        id=img.id,
        camera_id=img.camera_id,
        camera_name=names.get(img.camera_id or 0),
        product_id=img.product_id,
        stream=img.stream,
        crop=img.crop,
        width=img.width,
        height=img.height,
        source=img.source,
        status=img.status,
        is_empty=img.is_empty,
        captured_at=img.captured_at,
        annotations=[
            AnnotationIO(
                id=a.id,
                product_id=a.product_id,
                bbox=tuple(a.bbox),
                packaging=a.packaging,  # type: ignore[arg-type]
                status=a.status,
                confidence=a.confidence,
                touching=a.touching,
            )
            for a in img.annotations
        ],
    )


@router.get("/images", response_model=ImagesPage)
async def list_images(
    session: SessionDep,
    camera_id: int | None = None,
    product_id: int | None = None,
    status: Literal["unlabeled", "auto", "confirmed", "empty"] | None = None,
    source: Literal["manual", "auto", "count"] | None = None,
    day: date | None = None,
    offset: int = 0,
    limit: int = Query(60, le=500),
) -> ImagesPage:
    base = _filtered(camera_id, product_id, status, day, source)
    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (
            await session.execute(
                base.order_by(DatasetImage.captured_at.desc(), DatasetImage.id.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    names = await _cam_names(session)
    scope = _filtered(camera_id, product_id, None, day, source).subquery()
    cnt = dict((await session.execute(select(scope.c.status, func.count()).group_by(scope.c.status))).all())
    cnt["empty"] = (
        await session.execute(select(func.count()).select_from(scope).where(scope.c.is_empty.is_(True)))
    ).scalar_one()
    cnt["all"] = sum(v for k, v in cnt.items() if k != "empty")
    return ImagesPage(items=[ImageOut(**_img_out(i, names)) for i in rows], total=total, counts=cnt)


@router.get("/images/{image_id}", response_model=ImageDetail)
async def get_image(
    image_id: int,
    session: SessionDep,
    camera_id: int | None = None,
    product_id: int | None = None,
    status: Literal["unlabeled", "auto", "confirmed", "empty"] | None = None,
    source: Literal["manual", "auto", "count"] | None = None,
    day: date | None = None,
) -> ImageDetail:
    img = await session.get(DatasetImage, image_id)
    if img is None:
        raise not_found("Rasm topilmadi")
    names = await _cam_names(session)
    base = _filtered(camera_id, product_id, status, day, source).subquery()
    ordered = select(base.c.id).order_by(base.c.captured_at.desc(), base.c.id.desc())
    ids = [r for (r,) in (await session.execute(ordered)).all()]
    prev_id = next_id = position = None
    if image_id in ids:
        i = ids.index(image_id)
        position = i + 1
        prev_id = ids[i - 1] if i > 0 else None
        next_id = ids[i + 1] if i + 1 < len(ids) else None
    elif ids:
        next_id = ids[0]
    return ImageDetail(**_img_out(img, names), prev_id=prev_id, next_id=next_id, position=position, total=len(ids))


@router.get("/images/{image_id}/file")
async def image_file(image_id: int, session: SessionDep) -> FileResponse:
    img = await session.get(DatasetImage, image_id)
    if img is None:
        raise not_found("Rasm topilmadi")
    return FileResponse(
        abs_path(img.file_path), media_type="image/jpeg", headers={"Cache-Control": "max-age=86400, immutable"}
    )


@router.put("/images/{image_id}/annotations", response_model=ImageOut)
async def save_annotations(image_id: int, data: AnnotationsIn, session: SessionDep) -> ImageOut:
    img = await session.get(DatasetImage, image_id)
    if img is None:
        raise not_found("Rasm topilmadi")
    for a in data.annotations:
        x1, y1, x2, y2 = a.bbox
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise HTTPException(422, "Ramka kadr ichida va musbat o'lchamli bo'lishi kerak")
    await session.execute(delete(Annotation).where(Annotation.image_id == image_id))
    for a in data.annotations:
        session.add(
            Annotation(
                image_id=image_id,
                product_id=a.product_id,
                bbox=list(a.bbox),
                packaging=a.packaging,
                status=a.status,
                confidence=a.confidence,
                touching=a.touching,
            )
        )
    img.is_empty = data.is_empty and not data.annotations
    if data.annotations:
        img.status = "auto" if any(a.status == "auto" for a in data.annotations) else "confirmed"
    else:
        img.status = "confirmed" if img.is_empty else "unlabeled"
    await session.commit()
    await session.refresh(img, ["annotations"])
    return ImageOut(**_img_out(img, await _cam_names(session)))


@router.post("/images/confirm-auto")
async def confirm_auto(session: SessionDep, product_id: int | None = None, min_conf: float = 0.7) -> dict:
    """Ommaviy tasdiqlash: ishonchi yuqori bo'lgan avto takliflar."""
    stmt = select(DatasetImage).where(DatasetImage.status == "auto")
    imgs = (await session.execute(stmt)).scalars().all()
    n = 0
    for img in imgs:
        anns = img.annotations
        if product_id and not any(a.product_id == product_id for a in anns):
            continue
        if anns and all(a.status == "confirmed" or (a.confidence or 0) >= min_conf for a in anns):
            for a in anns:
                a.status = "confirmed"
            img.status = "confirmed"
            n += 1
    await session.commit()
    return {"confirmed": n}


def _unlink(rel: str) -> None:
    try:
        abs_path(rel).unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


@router.post("/images/delete")
async def bulk_delete(data: BulkDeleteIn, session: SessionDep) -> dict:
    """Ko'p rasmni o'chirish: ids bo'yicha yoki filtr bo'yicha (masalan, eski test snapshotlar)."""
    if data.ids:
        stmt = select(DatasetImage).where(DatasetImage.id.in_(data.ids))
    elif data.camera_id or data.product_id or data.source:
        stmt = _filtered(data.camera_id, data.product_id, None, None, data.source)
    else:
        raise HTTPException(422, "O'chirish uchun rasmlar yoki filtr ko'rsatilmagan")
    imgs = (await session.execute(stmt)).scalars().all()
    for img in imgs:
        _unlink(img.file_path)
        await session.delete(img)
    await session.commit()
    return {"deleted": len(imgs)}


@router.delete("/images/{image_id}", status_code=204)
async def delete_image(image_id: int, session: SessionDep) -> Response:
    img = await session.get(DatasetImage, image_id)
    if img is None:
        raise not_found("Rasm topilmadi")
    _unlink(img.file_path)
    await session.delete(img)
    await session.commit()
    return Response(status_code=204)


@router.post("/snapshot", response_model=ImageOut, status_code=201)
async def take_snapshot(data: SnapshotIn, session: SessionDep, redis: RedisDep) -> ImageOut:
    """Qo'lda snapshot — kameraning tahlil oqimidan (train va inference bir xil oqimda bo'lishi uchun)."""
    cam = await session.get(Camera, data.camera_id)
    if cam is None:
        raise not_found("Kamera topilmadi")
    if data.product_id and await session.get(Product, data.product_id) is None:
        raise not_found("Mahsulot topilmadi")
    roi = await camera_roi(session, cam.id) if data.mode == "roi" else None
    if data.mode == "roi" and not roi:
        raise HTTPException(409, "Bu kamerada ROI chizilmagan: avval vazifa sozlamasida ROI hududini chizing")
    kind = "sub" if cam.analysis_stream == "sub" and cam.sub_rtsp_url else "main"
    res = await grab_live_frame(redis, cam.id, kind)
    if res is None:
        raise HTTPException(503, "Kameradan kadr olib bo'lmadi: kamera ulanganini tekshiring")
    frame, _ = res
    crop = None
    if roi:
        fh, fw = frame.shape[:2]
        x1, y1, x2, y2 = roi_crop_box(roi, fw, fh)
        if (x1, y1, x2, y2) != (0, 0, fw, fh):
            frame = frame[y1:y2, x1:x2].copy()
            crop = [x1 / fw, y1 / fh, x2 / fw, y2 / fh]
    rel = save_jpeg(frame, task_dir(await images_root(session), cam.id, "counting") / "dataset")
    img = DatasetImage(
        camera_id=cam.id,
        product_id=data.product_id,
        crop=crop,
        stream=kind,
        file_path=rel,
        width=frame.shape[1],
        height=frame.shape[0],
        source="manual",
        status="unlabeled",
        phash=dhash(frame),
    )
    session.add(img)
    await session.commit()
    await session.refresh(img, ["annotations"])
    return ImageOut(**_img_out(img, {cam.id: cam.name}))


async def camera_roi(session, camera_id: int) -> list | None:
    """Kameraning ROI hududi: sanash ROI, bo'lmasa uskuna ROI (avto-yig'ish bilan bir xil tartib)."""
    for model in (CountingConfig, EquipmentConfig):
        cfg = await session.get(model, camera_id)
        if cfg is not None and cfg.roi_polygon:
            return cfg.roi_polygon
    return None


@router.get("/roi/{camera_id}")
async def get_roi(camera_id: int, session: SessionDep) -> dict:
    """Snapshot oldidan ko'rsatish uchun: ROI poligoni va kesim to'rtburchagi (0–1)."""
    roi = await camera_roi(session, camera_id)
    box = None
    if roi:
        x1, y1, x2, y2 = roi_crop_box(roi, 10000, 10000)
        box = [x1 / 10000, y1 / 10000, x2 / 10000, y2 / 10000]
    return {"roi": roi, "crop": box}


@router.get("/autocollect")
async def get_autocollect(session: SessionDep) -> dict:
    return await get_setting(session, "dataset.autocollect")


@router.put("/autocollect/{camera_id}")
async def put_autocollect(camera_id: int, data: AutoCollectIn, session: SessionDep, redis: RedisDep) -> dict:
    cur = dict(await get_setting(session, "dataset.autocollect") or {})
    cur[str(camera_id)] = data.model_dump()
    await set_setting(session, "dataset.autocollect", cur)
    from app.services import bus

    await bus.task_changed(redis, camera_id, None)
    return cur


class ReadinessRow(BaseModel):
    product_id: int
    code: str
    name: str
    objects: int
    confirmed: int
    auto: int
    boxed: int
    unboxed: int
    touching: int
    images: int
    negatives: int
    per_camera: dict[str, int]
    per_stream: dict[str, int]
    level: Literal["insufficient", "minimal", "ready"]


@router.get("/readiness", response_model=list[ReadinessRow])
async def readiness(session: SessionDep, product_id: int | None = None) -> list[ReadinessRow]:
    thr = await get_setting(session, "dataset.readiness")
    prods = (await session.execute(select(Product).order_by(Product.name))).scalars().all()
    if product_id:
        prods = [p for p in prods if p.id == product_id]
    rows = (
        await session.execute(
            select(
                Annotation.product_id,
                Annotation.status,
                Annotation.packaging,
                Annotation.touching,
                DatasetImage.id,
                DatasetImage.camera_id,
                DatasetImage.stream,
            ).join(DatasetImage, DatasetImage.id == Annotation.image_id)
        )
    ).all()
    names = await _cam_names(session)
    total_images = (
        await session.execute(select(func.count()).select_from(DatasetImage).where(DatasetImage.status != "unlabeled"))
    ).scalar_one()
    stat: dict[int, dict] = {}
    for pid, st, pack, touch, img_id, cam_id, stream in rows:
        d = stat.setdefault(
            pid,
            {
                "objects": 0,
                "confirmed": 0,
                "auto": 0,
                "boxed": 0,
                "unboxed": 0,
                "touching": 0,
                "images": set(),
                "per_camera": {},
                "per_stream": {},
            },
        )
        d["objects"] += 1
        d["confirmed" if st == "confirmed" else "auto"] += 1
        d["boxed" if pack == "boxed" else "unboxed"] += 1
        d["touching"] += int(bool(touch))
        d["images"].add(img_id)
        cn = names.get(cam_id or 0, "—")
        d["per_camera"][cn] = d["per_camera"].get(cn, 0) + 1
        d["per_stream"][stream] = d["per_stream"].get(stream, 0) + 1
    out = []
    for p in prods:
        d = stat.get(p.id) or {
            "objects": 0,
            "confirmed": 0,
            "auto": 0,
            "boxed": 0,
            "unboxed": 0,
            "touching": 0,
            "images": set(),
            "per_camera": {},
            "per_stream": {},
        }
        conf = d["confirmed"]
        level = "ready" if conf >= thr["ready"] else ("minimal" if conf >= thr["minimal"] else "insufficient")
        out.append(
            ReadinessRow(
                product_id=p.id,
                code=p.code,
                name=p.name,
                objects=d["objects"],
                confirmed=conf,
                auto=d["auto"],
                boxed=d["boxed"],
                unboxed=d["unboxed"],
                touching=d["touching"],
                images=len(d["images"]),
                negatives=max(0, total_images - len(d["images"])),
                per_camera=d["per_camera"],
                per_stream=d["per_stream"],
                level=level,
            )
        )  # type: ignore[arg-type]
    return out


def is_duplicate(h: int, recent: list[int], max_dist: int = 4) -> bool:
    return any(hamming(h, r) <= max_dist for r in recent)
