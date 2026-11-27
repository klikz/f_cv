"""Sanash: faol mahsulotlar, sanoqlar jurnali, tuzatish, qo'lda sanoq, o'lcham o'rganish, chalkash juftliklar."""

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core import keys
from app.core.config import get_settings
from app.models.cameras import Camera
from app.models.catalog import Annotation, DatasetImage, ModelVersion, Product
from app.models.counting import CountEvent, CountingConfigProduct, ManualCount
from app.models.tasks import CameraTask, CountingConfig
from app.services import bus
from app.services.images import abs_path, dhash
from app.services.render import render_snapshot

router = APIRouter(tags=["counting"])


# ---------- kameraning faol mahsulotlari ----------
class CamProduct(BaseModel):
    product_id: int
    name: str
    code: str
    model_version_id: int | None = None  # bo'sh — faol versiya
    active_version: int | None = None
    engine_ready: bool = False
    size_min: float | None = None
    size_max: float | None = None


class CamProductsIn(BaseModel):
    items: list[CamProduct] = Field(default_factory=list)


class CamProductsOut(BaseModel):
    items: list[CamProduct]
    available: list[CamProduct]
    load: dict


async def _active_versions(session, camera_id: int) -> dict[int, ModelVersion]:
    """Har mahsulot uchun faol versiya: kameraga xos bo'lsa o'sha, bo'lmasa umumiy (vision worker bilan bir xil)."""
    rows = (
        await session.execute(
            select(ModelVersion).where(
                ModelVersion.is_active.is_(True),
                (ModelVersion.camera_id == camera_id) | ModelVersion.camera_id.is_(None),
            )
        )
    ).scalars()
    out: dict[int, ModelVersion] = {}
    for r in rows:
        if r.product_id not in out or r.camera_id is not None:
            out[r.product_id] = r
    return out


async def _load_info(session, redis) -> dict:
    """GPU yuklama: Σ kameralar (inference fps × faol mahsulotlar)."""
    cfgs = {c.camera_id: c for c in (await session.execute(select(CountingConfig))).scalars()}
    enabled = set(
        (
            await session.execute(
                select(CameraTask.camera_id).where(CameraTask.task_type == "counting", CameraTask.enabled.is_(True))
            )
        ).scalars()
    )
    counts = dict(
        (
            await session.execute(
                select(CountingConfigProduct.camera_id, func.count()).group_by(CountingConfigProduct.camera_id)
            )
        ).all()
    )
    per_cam = {cid: round(float(cfgs[cid].inference_fps) * counts.get(cid, 0), 1) for cid in enabled if cid in cfgs}
    from app.services.settings_store import get_setting

    budget = await get_setting(session, "inference.max_load")
    st = await redis.hgetall(keys.INFERENCE_STATS)
    return {
        "per_camera": per_cam,
        "total": round(sum(per_cam.values()), 1),
        "budget": budget,
        "rps": float(st.get("rps", 0) or 0),
        "latency_ms": float(st.get("latency_ms", 0) or 0),
        "fps_scale": float(st.get("fps_scale", 1) or 1),
        "vram_mb": float(st.get("vram_mb", 0) or 0),
    }


@router.get("/cameras/{camera_id}/counting/products", response_model=CamProductsOut)
async def get_cam_products(camera_id: int, session: SessionDep, redis: RedisDep) -> CamProductsOut:
    if await session.get(Camera, camera_id) is None:
        raise not_found("Kamera topilmadi")
    prods = {p.id: p for p in (await session.execute(select(Product).order_by(Product.name))).scalars()}
    act = await _active_versions(session, camera_id)
    rows = (
        (await session.execute(select(CountingConfigProduct).where(CountingConfigProduct.camera_id == camera_id)))
        .scalars()
        .all()
    )
    items = []
    for r in rows:
        p = prods.get(r.product_id)
        if p is None:
            continue
        mv = act.get(p.id)
        items.append(
            CamProduct(
                product_id=p.id,
                name=p.name,
                code=p.code,
                model_version_id=r.model_version_id,
                active_version=mv.version if mv else None,
                engine_ready=bool(mv and mv.engine_path and mv.status == "ready"),
                size_min=r.size_min,
                size_max=r.size_max,
            )
        )
    chosen = {i.product_id for i in items}
    available = [
        CamProduct(
            product_id=p.id,
            name=p.name,
            code=p.code,
            active_version=act[p.id].version,
            engine_ready=bool(act[p.id].engine_path and act[p.id].status == "ready"),
        )
        for p in prods.values()
        if p.id in act and p.id not in chosen
    ]
    return CamProductsOut(items=items, available=available, load=await _load_info(session, redis))


@router.put("/cameras/{camera_id}/counting/products", response_model=CamProductsOut)
async def put_cam_products(camera_id: int, data: CamProductsIn, session: SessionDep, redis: RedisDep) -> CamProductsOut:
    if await session.get(Camera, camera_id) is None:
        raise not_found("Kamera topilmadi")
    act = await _active_versions(session, camera_id)
    existing = {
        r.product_id: r
        for r in (
            await session.execute(select(CountingConfigProduct).where(CountingConfigProduct.camera_id == camera_id))
        ).scalars()
    }
    want = {i.product_id: i for i in data.items}
    for pid in want:
        if pid not in act:
            raise HTTPException(422, "Faqat faol modeli bor mahsulotni tanlash mumkin")
    for pid, row in existing.items():
        if pid not in want:
            await session.delete(row)
    for pid, it in want.items():
        row = existing.get(pid)
        if row is None:
            row = CountingConfigProduct(camera_id=camera_id, product_id=pid)
            session.add(row)
        row.model_version_id = it.model_version_id
    await session.commit()
    await bus.task_changed(redis, camera_id, "counting")
    return await get_cam_products(camera_id, session, redis)


@router.put("/cameras/{camera_id}/counting/testmode")
async def set_testmode(camera_id: int, redis: RedisDep, enabled: bool = True) -> dict:
    """Jonli test: aniqlashlar va "sanalgan bo'lardi" belgisi bazaga yozilmasdan (10 daqiqa)."""
    key = f"fcv:testmode:{camera_id}"
    if enabled:
        await redis.set(key, "1", ex=600)
    else:
        await redis.delete(key)
    await bus.task_changed(redis, camera_id, "counting")
    return {"enabled": enabled}


@router.get("/counting/load")
async def counting_load(session: SessionDep, redis: RedisDep) -> dict:
    return await _load_info(session, redis)


# ---------- sanoqlar jurnali ----------
class EventOut(BaseModel):
    id: int
    camera_id: int | None
    camera_name: str | None
    product_id: int | None
    product_name: str | None
    original_product_id: int | None
    original_product_name: str | None
    status: str
    candidates: list[dict]
    direction: str
    confidence: float | None
    bbox: list[float] | None
    ts: datetime
    shift_id: int | None
    shift_date: date | None
    has_snapshot: bool
    corrected_at: datetime | None
    note: str | None


class EventsPage(BaseModel):
    items: list[EventOut]
    total: int
    summary: dict


def _events_query(camera_id, product_id, status, day_from, day_to, shift_id):
    q = select(CountEvent)
    if camera_id:
        q = q.where(CountEvent.camera_id == camera_id)
    if product_id:
        q = q.where(CountEvent.product_id == product_id)
    if status:
        q = q.where(CountEvent.status == status)
    tz = ZoneInfo(get_settings().timezone)
    if day_from:
        q = q.where(CountEvent.ts >= datetime.combine(day_from, datetime.min.time(), tz))
    if day_to:
        q = q.where(CountEvent.ts < datetime.combine(day_to + timedelta(days=1), datetime.min.time(), tz))
    if shift_id:
        q = q.where(CountEvent.shift_id == shift_id)
    return q


async def _names(session):
    return dict((await session.execute(select(Product.id, Product.name))).all()), dict(
        (await session.execute(select(Camera.id, Camera.name))).all()
    )


def _ev(e: CountEvent, pn: dict, cn: dict) -> EventOut:
    return EventOut(
        id=e.id,
        camera_id=e.camera_id,
        camera_name=cn.get(e.camera_id or 0),
        product_id=e.product_id,
        product_name=pn.get(e.product_id or 0),
        original_product_id=e.original_product_id,
        original_product_name=pn.get(e.original_product_id or 0),
        status=e.status,
        candidates=[{**c, "name": pn.get(c.get("product_id"))} for c in (e.candidates or [])],
        direction=e.direction,
        confidence=e.confidence,
        bbox=e.bbox,
        ts=e.ts,
        shift_id=e.shift_id,
        shift_date=e.shift_date,
        has_snapshot=bool(e.snapshot_path),
        corrected_at=e.corrected_at,
        note=e.note,
    )


@router.get("/counts", response_model=EventsPage)
async def list_events(
    session: SessionDep,
    camera_id: int | None = None,
    product_id: int | None = None,
    status: Literal["confirmed", "uncertain", "corrected", "cancelled"] | None = None,
    day_from: date | None = None,
    day_to: date | None = None,
    shift_id: int | None = None,
    offset: int = 0,
    limit: int = Query(50, le=500),
) -> EventsPage:
    q = _events_query(camera_id, product_id, status, day_from, day_to, shift_id)
    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await session.execute(q.order_by(CountEvent.ts.desc()).offset(offset).limit(limit))).scalars().all()
    base = _events_query(camera_id, product_id, None, day_from, day_to, shift_id).subquery()
    summary = dict((await session.execute(select(base.c.status, func.count()).group_by(base.c.status))).all())
    pn, cn = await _names(session)
    return EventsPage(items=[_ev(e, pn, cn) for e in rows], total=total, summary=summary)


@router.get("/counts/{event_id}", response_model=EventOut)
async def get_event(event_id: int, session: SessionDep) -> EventOut:
    e = await session.get(CountEvent, event_id)
    if e is None:
        raise not_found("Sanoq topilmadi")
    pn, cn = await _names(session)
    return _ev(e, pn, cn)


@router.get("/counts/{event_id}/snapshot")
async def event_snapshot(event_id: int, session: SessionDep, raw: bool = False):
    """Sanoq snapshoti: sanalgan mahsulot ramkasi va nomi bilan (raw=1 — toza kadr)."""
    e = await session.get(CountEvent, event_id)
    if e is None or not e.snapshot_path:
        raise not_found("Snapshot yo'q")
    if raw:
        return FileResponse(abs_path(e.snapshot_path), media_type="image/jpeg")
    p = await session.get(Product, e.product_id) if e.product_id else None
    label = (p.name if p else "Noaniq") + (" (noaniq)" if e.status == "uncertain" else "")
    color = (60, 200, 255) if e.status == "uncertain" else (80, 220, 120)
    try:
        data = render_snapshot(e.snapshot_path, e.bbox, label, color)
    except FileNotFoundError as ex:
        raise not_found("Snapshot fayli topilmadi") from ex
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "max-age=60"})


class CorrectIn(BaseModel):
    action: Literal["set_product", "cancel", "restore"]
    product_id: int | None = None
    note: str | None = None


@router.post("/counts/{event_id}/correct", response_model=EventOut)
async def correct_event(event_id: int, data: CorrectIn, session: SessionDep, redis: RedisDep) -> EventOut:
    """Tuzatish: mahsulotni o'zgartirish yoki yolg'on sanoqni bekor qilish. Asl qiymat saqlanadi (audit)."""
    e = await session.get(CountEvent, event_id)
    if e is None:
        raise not_found("Sanoq topilmadi")
    if data.action == "set_product":
        if not data.product_id or await session.get(Product, data.product_id) is None:
            raise HTTPException(422, "Mahsulotni tanlang")
        e.product_id = data.product_id
        e.status = "corrected" if data.product_id != e.original_product_id else "confirmed"
    elif data.action == "cancel":
        e.status = "cancelled"
    else:
        e.status = "corrected" if e.product_id != e.original_product_id else "confirmed"
    e.corrected_at = datetime.now(UTC)
    if data.note is not None:
        e.note = data.note
    await session.commit()
    if e.camera_id:
        await bus.task_changed(redis, e.camera_id, "counting")  # joriy smena hisoblagichi bazadan qayta tiklanadi
    await bus.emit_event(redis, "count_corrected", {"event_id": e.id, "camera_id": e.camera_id})
    pn, cn = await _names(session)
    return _ev(e, pn, cn)


@router.post("/counts/{event_id}/to-dataset")
async def event_to_dataset(event_id: int, session: SessionDep) -> dict:
    """Tuzatilgan sanoq snapshotini bir tugma bilan datasetga qo'shish (ramka bilan, tasdiqlangan)."""
    e = await session.get(CountEvent, event_id)
    if e is None or not e.snapshot_path:
        raise not_found("Snapshot yo'q")
    if not e.product_id or e.status in ("uncertain", "cancelled"):
        raise HTTPException(422, "Avval sanoqni tuzating (mahsulotni tanlang)")
    exists = (
        await session.execute(select(DatasetImage.id).where(DatasetImage.file_path == e.snapshot_path))
    ).scalar_one_or_none()
    if exists:
        return {"image_id": exists, "created": False}
    img = cv2.imread(str(abs_path(e.snapshot_path)))
    if img is None:
        raise not_found("Snapshot fayli topilmadi")
    cam = await session.get(Camera, e.camera_id) if e.camera_id else None
    di = DatasetImage(
        camera_id=e.camera_id,
        stream=cam.analysis_stream if cam else "main",
        file_path=e.snapshot_path,
        width=img.shape[1],
        height=img.shape[0],
        source="count",
        status="confirmed",
        phash=dhash(img),
    )
    session.add(di)
    await session.flush()
    if e.bbox:
        session.add(Annotation(image_id=di.id, product_id=e.product_id, bbox=e.bbox, status="confirmed"))
    await session.commit()
    return {"image_id": di.id, "created": True}


# ---------- aniqlikni tekshirish ----------
class ManualIn(BaseModel):
    camera_id: int
    product_id: int | None = None
    start_ts: datetime
    end_ts: datetime
    count: int = Field(ge=0)
    note: str | None = None


class ManualOut(ManualIn):
    id: int
    system_count: int
    diff: int
    accuracy_pct: float | None
    camera_name: str | None = None
    product_name: str | None = None


async def _system_count(session, camera_id: int, product_id: int | None, a: datetime, b: datetime) -> int:
    q = select(CountEvent.direction, func.count()).where(
        CountEvent.camera_id == camera_id, CountEvent.ts >= a, CountEvent.ts < b, CountEvent.status != "cancelled"
    )
    if product_id:
        q = q.where(CountEvent.product_id == product_id)
    rows = dict((await session.execute(q.group_by(CountEvent.direction))).all())
    cfg = await session.get(CountingConfig, camera_id)
    fwd, rev = rows.get("forward", 0), rows.get("reverse", 0)
    if cfg and cfg.direction != "both" and cfg.reverse_policy == "subtract":
        return fwd - rev
    return fwd + (rev if cfg and cfg.direction == "both" else 0)


async def _manual_out(session, m: ManualCount, pn, cn) -> ManualOut:
    sysc = await _system_count(session, m.camera_id, m.product_id, m.start_ts, m.end_ts)
    acc = (100.0 - abs(sysc - m.count) / m.count * 100.0) if m.count else None
    return ManualOut(
        id=m.id,
        camera_id=m.camera_id,
        product_id=m.product_id,
        start_ts=m.start_ts,
        end_ts=m.end_ts,
        count=m.count,
        note=m.note,
        system_count=sysc,
        diff=sysc - m.count,
        accuracy_pct=round(acc, 2) if acc is not None else None,
        camera_name=cn.get(m.camera_id),
        product_name=pn.get(m.product_id or 0),
    )


@router.get("/manual-counts", response_model=list[ManualOut])
async def list_manual(session: SessionDep) -> list[ManualOut]:
    pn, cn = await _names(session)
    rows = (await session.execute(select(ManualCount).order_by(ManualCount.start_ts.desc()).limit(200))).scalars().all()
    return [await _manual_out(session, m, pn, cn) for m in rows]


@router.post("/manual-counts", response_model=ManualOut, status_code=201)
async def add_manual(data: ManualIn, session: SessionDep) -> ManualOut:
    if data.end_ts <= data.start_ts:
        raise HTTPException(422, "Tugash vaqti boshlanishdan keyin bo'lishi kerak")
    m = ManualCount(**data.model_dump())
    session.add(m)
    await session.commit()
    pn, cn = await _names(session)
    return await _manual_out(session, m, pn, cn)


@router.delete("/manual-counts/{mid}", status_code=204)
async def del_manual(mid: int, session: SessionDep) -> Response:
    m = await session.get(ManualCount, mid)
    if m is None:
        raise not_found()
    await session.delete(m)
    await session.commit()
    return Response(status_code=204)


# ---------- o'rganuvchi yordamchilar ----------
@router.post("/cameras/{camera_id}/counting/learn-sizes")
async def learn_sizes(camera_id: int, session: SessionDep, redis: RedisDep, min_samples: int = 20) -> dict:
    """Kutilgan bbox o'lcham oralig'ini tasdiqlangan sanoqlardan o'rganish (dizayni bir xil, o'lchami farqli mahsulotlar)."""
    rows = (
        await session.execute(
            select(CountEvent.product_id, CountEvent.bbox)
            .where(
                CountEvent.camera_id == camera_id,
                CountEvent.status.in_(["confirmed", "corrected"]),
                CountEvent.bbox.isnot(None),
            )
            .order_by(CountEvent.ts.desc())
            .limit(5000)
        )
    ).all()
    areas: dict[int, list[float]] = {}
    for pid, bb in rows:
        if pid and bb:
            areas.setdefault(pid, []).append((bb[2] - bb[0]) * (bb[3] - bb[1]))
    out = {}
    cps = {
        r.product_id: r
        for r in (
            await session.execute(select(CountingConfigProduct).where(CountingConfigProduct.camera_id == camera_id))
        ).scalars()
    }
    for pid, a in areas.items():
        if len(a) < min_samples or pid not in cps:
            continue
        lo, hi = float(np.percentile(a, 5)) * 0.85, float(np.percentile(a, 95)) * 1.15
        cps[pid].size_min, cps[pid].size_max = round(lo, 5), round(hi, 5)
        out[pid] = {"samples": len(a), "min": lo, "max": hi}
    await session.commit()
    await bus.task_changed(redis, camera_id, "counting")
    return {"learned": out}


@router.get("/counting/confused-pairs")
async def confused_pairs(session: SessionDep, days: int = 30) -> list[dict]:
    """Tuzatishlar statistikasi: qaysi mahsulot qaysi biri bilan chalkashtirilgan → qayta train taklifi."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await session.execute(
            select(CountEvent.original_product_id, CountEvent.product_id, func.count())
            .where(
                CountEvent.status == "corrected",
                CountEvent.corrected_at >= since,
                and_(CountEvent.original_product_id.isnot(None), CountEvent.product_id.isnot(None)),
            )
            .group_by(CountEvent.original_product_id, CountEvent.product_id)
        )
    ).all()
    pn, _ = await _names(session)
    out = [
        {"predicted_id": a, "predicted": pn.get(a), "actual_id": b, "actual": pn.get(b), "count": n}
        for a, b, n in rows
        if a != b
    ]
    return sorted(out, key=lambda x: -x["count"])
