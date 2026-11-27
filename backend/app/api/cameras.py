"""Kameralar CRUD, oqimni tekshirish, kadr olish."""

import asyncio
import base64

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from sqlalchemy import delete, func, select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core.db import get_sessionmaker
from app.models.cameras import Camera, CameraStream
from app.schemas.cameras import (
    CameraCreate,
    CameraOut,
    CameraUpdate,
    PreviewIn,
    PreviewOut,
    ProbeIn,
    ProbeOut,
    ReorderIn,
)
from app.services import bus
from app.services.cameras import save_probe, to_out, unmask
from app.services.probe import grab_frame_jpeg, probe_stream

router = APIRouter(prefix="/cameras", tags=["cameras"])


async def _get(session, camera_id: int) -> Camera:
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise not_found("Kamera topilmadi")
    return cam


async def _probe_and_store(camera_id: int) -> None:
    """Fon vazifasi: kamera saqlangach oqimlar ma'lumotini (kodek/o'lcham/FPS) yozib qo'yish."""
    async with get_sessionmaker()() as s:
        cam = await s.get(Camera, camera_id)
        if cam is None:
            return
        targets = [("main", cam.main_rtsp_url)] + ([("sub", cam.sub_rtsp_url)] if cam.sub_rtsp_url else [])
        results = await asyncio.gather(*(probe_stream(u) for _, u in targets))
        for (kind, _), r in zip(targets, results, strict=True):
            await save_probe(s, camera_id, kind, r)
        await s.commit()


@router.get("", response_model=list[CameraOut])
async def list_cameras(session: SessionDep, redis: RedisDep) -> list[CameraOut]:
    cams = (await session.execute(select(Camera).order_by(Camera.position, Camera.id))).scalars().all()
    return [await to_out(c, redis) for c in cams]


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(camera_id: int, session: SessionDep, redis: RedisDep) -> CameraOut:
    return await to_out(await _get(session, camera_id), redis)


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(data: CameraCreate, session: SessionDep, redis: RedisDep, bg: BackgroundTasks) -> CameraOut:
    pos = (await session.execute(select(func.coalesce(func.max(Camera.position), -1)))).scalar_one() + 1
    cam = Camera(**data.model_dump(), position=pos, analysis_stream="main")
    session.add(cam)
    await session.commit()
    await session.refresh(cam, ["streams"])
    await bus.camera_changed(redis, "created", cam.id)
    bg.add_task(_probe_and_store, cam.id)
    return await to_out(cam, redis)


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: int, data: CameraUpdate, session: SessionDep, redis: RedisDep, bg: BackgroundTasks
) -> CameraOut:
    cam = await _get(session, camera_id)
    upd = data.model_dump(exclude_unset=True)
    urls_changed = False
    if upd.get("main_rtsp_url"):
        new = unmask(upd["main_rtsp_url"], cam.main_rtsp_url)
        urls_changed |= new != cam.main_rtsp_url
        cam.main_rtsp_url = new  # type: ignore[assignment]
    if upd.get("clear_sub"):
        if cam.sub_rtsp_url:
            urls_changed = True
        cam.sub_rtsp_url = None
        if cam.analysis_stream == "sub":
            cam.analysis_stream = "main"
        await session.execute(delete(CameraStream).where(CameraStream.camera_id == cam.id, CameraStream.kind == "sub"))
    elif "sub_rtsp_url" in upd:
        new = unmask(upd["sub_rtsp_url"], cam.sub_rtsp_url)
        urls_changed |= new != cam.sub_rtsp_url
        cam.sub_rtsp_url = new
        if not new and cam.analysis_stream == "sub":
            cam.analysis_stream = "main"
    for f in (
        "name",
        "enabled",
        "fov_match",
        "onvif_host",
        "onvif_port",
        "onvif_username",
        "onvif_main_profile",
        "onvif_sub_profile",
    ):
        if f in upd:
            setattr(cam, f, upd[f])
    if upd.get("onvif_password"):
        cam.onvif_password = upd["onvif_password"]
    await session.commit()
    await session.refresh(cam, ["streams", "updated_at"])
    await bus.camera_changed(redis, "updated", cam.id)
    if urls_changed:
        bg.add_task(_probe_and_store, cam.id)
    return await to_out(cam, redis)


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: int, session: SessionDep, redis: RedisDep) -> Response:
    cam = await _get(session, camera_id)
    await session.delete(cam)
    await session.commit()
    await bus.camera_changed(redis, "deleted", camera_id)
    return Response(status_code=204)


@router.post("/reorder", status_code=204)
async def reorder(data: ReorderIn, session: SessionDep, redis: RedisDep) -> Response:
    cams = {c.id: c for c in (await session.execute(select(Camera))).scalars()}
    for pos, cid in enumerate(data.ids):
        if cid in cams:
            cams[cid].position = pos
    await session.commit()
    await bus.camera_changed(redis, "reordered", 0)
    return Response(status_code=204)


async def _resolve_url(session, url: str | None, camera_id: int | None, kind: str | None) -> str:
    cam = await _get(session, camera_id) if camera_id else None
    if url:
        if cam is not None:
            old = cam.sub_rtsp_url if kind == "sub" else cam.main_rtsp_url
            return unmask(url, old) or url
        return url
    if cam is None:
        raise HTTPException(422, "Manzil yoki kamera ko'rsatilmagan")
    u = cam.sub_rtsp_url if kind == "sub" else cam.main_rtsp_url
    if not u:
        raise HTTPException(422, "Bu kamerada sub oqim yo'q")
    return u


@router.post("/probe", response_model=ProbeOut)
async def probe(data: ProbeIn, session: SessionDep) -> ProbeOut:
    url = await _resolve_url(session, data.url, data.camera_id, data.kind)
    r = await probe_stream(url)
    if data.camera_id and data.kind and not data.url:
        await save_probe(session, data.camera_id, data.kind, r)
        await session.commit()
    return ProbeOut(**r.__dict__)


@router.post("/preview", response_model=PreviewOut)
async def preview(data: PreviewIn, session: SessionDep) -> PreviewOut:
    """Main va sub kadrlarini yonma-yon solishtirish uchun (ko'rish maydoni bir xilmi)."""
    main_url = (
        await _resolve_url(session, data.main_url, data.camera_id, "main")
        if (data.main_url or data.camera_id)
        else None
    )
    sub_url = None
    if data.sub_url:
        sub_url = await _resolve_url(session, data.sub_url, data.camera_id, "sub")
    elif data.camera_id:
        cam = await _get(session, data.camera_id)
        sub_url = cam.sub_rtsp_url

    async def grab(u: str | None):
        if not u:
            return None, None
        return await grab_frame_jpeg(u)

    (m, me), (s, se) = await asyncio.gather(grab(main_url), grab(sub_url))
    enc = lambda b: "data:image/jpeg;base64," + base64.b64encode(b).decode() if b else None  # noqa: E731
    return PreviewOut(main=enc(m), sub=enc(s), main_error=me, sub_error=se)
