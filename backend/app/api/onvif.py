"""ONVIF: qidirish, qurilmani o'qish, kamerani ONVIF orqali yangilash."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core.urls import host_of
from app.models.cameras import Camera
from app.services import bus
from app.services.cameras import to_out
from vision.onvif.client import OnvifError, discover, read_device

router = APIRouter(prefix="/onvif", tags=["onvif"])


class ConnectIn(BaseModel):
    host: str
    port: int = 80
    username: str = ""
    password: str = ""


@router.get("/discover")
async def onvif_discover(session: SessionDep, timeout: float = 3.0) -> list[dict]:
    devices = await discover(min(max(timeout, 1.0), 10.0))
    cams = (await session.execute(select(Camera))).scalars().all()
    known = {c.onvif_host for c in cams if c.onvif_host} | {host_of(c.main_rtsp_url) for c in cams}
    return [{**d.__dict__, "already_added": d.host in known} for d in devices]


@router.post("/device")
async def onvif_device(data: ConnectIn) -> dict:
    try:
        info = await read_device(data.host, data.port, data.username, data.password)
    except OnvifError as e:
        raise HTTPException(422, str(e)) from e
    return info.as_dict()


@router.post("/cameras/{camera_id}/refresh")
async def onvif_refresh(camera_id: int, session: SessionDep, redis: RedisDep):
    """Kamera IP yoki manzillari o'zgarsa — ONVIF dan qayta o'qib, RTSP manzillarini yangilash."""
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise not_found("Kamera topilmadi")
    if not cam.onvif_host:
        raise HTTPException(422, "Bu kamera ONVIF orqali qo'shilmagan")
    try:
        info = await read_device(
            cam.onvif_host, cam.onvif_port or 80, cam.onvif_username or "", cam.onvif_password or ""
        )
    except OnvifError as e:
        raise HTTPException(422, str(e)) from e
    by_token = {p.token: p for p in info.profiles}
    main = by_token.get(cam.onvif_main_profile or "") or by_token.get(info.suggested_main or "")
    sub = by_token.get(cam.onvif_sub_profile or "") or by_token.get(info.suggested_sub or "")
    if main is None or not main.rtsp_url:
        raise HTTPException(422, "ONVIF dan asosiy oqim manzilini olib bo'lmadi")
    cam.main_rtsp_url = main.rtsp_url
    cam.onvif_main_profile = main.token
    if sub and sub.rtsp_url:
        cam.sub_rtsp_url = sub.rtsp_url
        cam.onvif_sub_profile = sub.token
    cam.onvif_manufacturer, cam.onvif_model, cam.onvif_serial = info.manufacturer, info.model, info.serial
    await session.commit()
    await session.refresh(cam, ["streams", "updated_at"])
    await bus.camera_changed(redis, "updated", cam.id)
    return {"camera": (await to_out(cam, redis)).model_dump(), "device": info.as_dict()}
