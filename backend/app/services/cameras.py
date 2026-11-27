"""Kamera bilan ishlash: maskalangan manzilni tiklash, oqim ma'lumotini yangilash."""

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import keys
from app.core.urls import credentials_of, mask_url
from app.models.cameras import Camera, CameraStream
from app.schemas.cameras import CameraOut, OnvifInfo, StreamInfo
from app.services.probe import ProbeResult

MASK = "•••"


def unmask(new_url: str | None, old_url: str | None) -> str | None:
    """UI maskalangan manzilni qaytarsa (parol o'zgarmagan) — eski parolni tiklaydi."""
    if not new_url or MASK not in new_url:
        return new_url
    if not old_url:
        return new_url.replace(f":{MASK}", "")
    _, pwd = credentials_of(old_url)
    if pwd is None:
        return new_url.replace(f":{MASK}", "")
    from urllib.parse import quote

    return new_url.replace(MASK, quote(pwd, safe=""), 1)


async def stream_live_status(redis: Redis, camera_id: int, kind: str) -> dict[str, str]:
    try:
        return await redis.hgetall(keys.stream_status(camera_id, kind))
    except Exception:
        return {}


async def to_out(cam: Camera, redis: Redis | None = None) -> CameraOut:
    streams: list[StreamInfo] = []
    by_kind = {s.kind: s for s in cam.streams}
    kinds = ["main"] + (["sub"] if cam.sub_rtsp_url else [])
    for kind in kinds:
        s = by_kind.get(kind)
        info = StreamInfo(
            kind=kind,  # type: ignore[arg-type]
            codec=s.codec if s else None,
            width=s.width if s else None,
            height=s.height if s else None,
            fps=s.fps if s else None,
            status=(s.status if s else "offline"),
            last_error=s.last_error if s else None,
        )
        if redis is not None:
            live = await stream_live_status(redis, cam.id, kind)
            if live:
                info.status = live.get("status", info.status)
                info.last_error = live.get("error") or None
                if live.get("width"):
                    info.width = int(live["width"])
                    info.height = int(live["height"])
        streams.append(info)
    onvif = None
    if cam.connection_type == "onvif" or cam.onvif_host:
        onvif = OnvifInfo(
            host=cam.onvif_host,
            port=cam.onvif_port,
            username=cam.onvif_username,
            manufacturer=cam.onvif_manufacturer,
            model=cam.onvif_model,
            serial=cam.onvif_serial,
            main_profile=cam.onvif_main_profile,
            sub_profile=cam.onvif_sub_profile,
        )
    return CameraOut(
        id=cam.id,
        name=cam.name,
        enabled=cam.enabled,
        position=cam.position,
        connection_type=cam.connection_type,
        main_rtsp_url=mask_url(cam.main_rtsp_url) or "",
        sub_rtsp_url=mask_url(cam.sub_rtsp_url),
        analysis_stream=cam.analysis_stream,  # type: ignore[arg-type]
        fov_match=cam.fov_match,
        onvif=onvif,
        streams=streams,
        created_at=cam.created_at,
        updated_at=cam.updated_at,
    )


async def save_probe(session: AsyncSession, camera_id: int, kind: str, r: ProbeResult) -> None:
    row = (
        await session.execute(
            select(CameraStream).where(CameraStream.camera_id == camera_id, CameraStream.kind == kind)
        )
    ).scalar_one_or_none()
    if row is None:
        row = CameraStream(camera_id=camera_id, kind=kind)
        session.add(row)
    if r.ok:
        row.codec, row.width, row.height, row.fps = r.codec, r.width, r.height, r.fps
        row.last_error = None
    else:
        row.last_error = r.error
    row.updated_at = datetime.now(UTC)
