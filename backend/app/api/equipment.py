"""Uskuna: jonli signal, tayanch kadr, avto-aniqlash, intervallar/sikllar."""

import time
from datetime import UTC, datetime

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core import keys
from app.core.files import atomic_write_bytes
from app.models.cameras import Camera
from app.models.equipment import CycleEvent, EquipmentInterval
from app.models.tasks import EquipmentConfig
from app.services import bus
from app.services.images import abs_path, images_root, task_dir, to_stored
from app.services.snapshot import grab_live_frame
from vision.motion.signal import autocorr_period

router = APIRouter(prefix="/cameras/{camera_id}/equipment", tags=["equipment"])


@router.get("/signal")
async def signal(
    camera_id: int, redis: RedisDep, seconds: int = Query(300, ge=10, le=10800), max_points: int = 1500
) -> dict:
    """Jonli harakat signali (Redis'dan): t, harakat %, tayanchdan farq %, holat."""
    since = int((time.time() - seconds) * 1000)
    rows = await redis.xrange(keys.motion_signal(camera_id), min=f"{since}-0", max="+")
    step = max(1, len(rows) // max_points)
    pts = [[float(f["t"]), float(f["m"]), float(f.get("h", 0)), f.get("s", "u")] for _, f in rows[::step]]
    return {"points": pts}


@router.get("/cycles")
async def recent_cycles(camera_id: int, session: SessionDep, seconds: int = 300) -> list[dict]:
    since = datetime.fromtimestamp(time.time() - seconds, UTC)
    rows = (
        await session.execute(
            select(CycleEvent)
            .where(CycleEvent.camera_id == camera_id, CycleEvent.end_ts >= since)
            .order_by(CycleEvent.end_ts)
        )
    ).scalars()
    return [
        {"start": c.start_ts.timestamp(), "end": c.end_ts.timestamp(), "duration": c.duration, "micro": c.is_micro_stop}
        for c in rows
    ]


async def _cfg(session, camera_id: int) -> EquipmentConfig:
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise not_found("Kamera topilmadi")
    cfg = await session.get(EquipmentConfig, camera_id)
    if cfg is None:
        cfg = EquipmentConfig(camera_id=camera_id, stream=cam.analysis_stream)
        session.add(cfg)
        await session.flush()
    return cfg


@router.post("/home")
async def capture_home(camera_id: int, session: SessionDep, redis: RedisDep, from_candidate: bool = False) -> dict:
    """Tayanch ("uy") kadrni olish: joriy kadr (tugma) yoki avtomatik taklif (eng so'nggi tinch holat)."""
    cfg = await _cfg(session, camera_id)
    cam = await session.get(Camera, camera_id)
    folder = task_dir(await images_root(session), camera_id, "equipment")
    if from_candidate:
        cand = folder / "home_candidate.jpg"
        if not cand.exists():
            raise HTTPException(404, "Tinch holat kadri hali yo'q — uskuna to'xtagan paytni kuting")
        img = cv2.imread(str(cand))
    else:
        kind = "sub" if cam and cam.analysis_stream == "sub" and cam.sub_rtsp_url else "main"
        res = await grab_live_frame(redis, camera_id, kind)
        if res is None:
            raise HTTPException(503, "Kameradan kadr olib bo'lmadi")
        img = res[0]
    if img is None:
        raise HTTPException(500, "Kadr o'qilmadi")
    path = folder / f"home_{int(time.time())}.png"
    ok, buf = cv2.imencode(".png", img)
    atomic_write_bytes(path, buf.tobytes())
    rel = to_stored(path)
    cfg.home_reference = rel
    await session.commit()
    await bus.task_changed(redis, camera_id, "equipment")
    return {"home_reference": rel}


@router.get("/home.jpg")
async def home_image(camera_id: int, session: SessionDep, candidate: bool = False):
    if candidate:
        p = task_dir(await images_root(session), camera_id, "equipment") / "home_candidate.jpg"
        if not p.exists():
            raise not_found("Taklif yo'q")
        return FileResponse(p, headers={"Cache-Control": "no-cache"})
    cfg = await session.get(EquipmentConfig, camera_id)
    if cfg is None or not cfg.home_reference:
        raise not_found("Tayanch kadr olinmagan")
    img = cv2.imread(str(abs_path(cfg.home_reference)))
    if img is None:
        raise not_found("Tayanch kadr fayli topilmadi")
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(buf.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.post("/autodetect")
async def autodetect(camera_id: int, redis: RedisDep, seconds: int = 180) -> dict:
    """Avto-aniqlash: avtokorrelyatsiya bilan davr, cho'qqilar soni K va chegaralar taklifi."""
    since = int((time.time() - seconds) * 1000)
    rows = await redis.xrange(keys.motion_signal(camera_id), min=f"{since}-0", max="+")
    if len(rows) < 100:
        raise HTTPException(422, "Signal yetarli emas — uskuna ishlayotgan paytda 1–3 daqiqa kuting")
    t = np.array([float(f["t"]) for _, f in rows])
    m = np.array([float(f["m"]) for _, f in rows])
    hd = np.array([float(f.get("h", 0)) for _, f in rows])
    fps = max(1.0, (len(t) - 1) / max(1e-6, t[-1] - t[0]))
    active = m > np.percentile(m, 20) + 0.5
    period = autocorr_period(m, fps)
    if period is None:
        raise HTTPException(422, "Takrorlanuvchi harakat topilmadi")
    # bir davrdagi cho'qqilar soni
    from scipy.signal import find_peaks

    hi = float(np.percentile(m[active], 75)) if active.any() else float(m.max())
    peaks, _ = find_peaks(m, height=hi * 0.5, distance=max(1, int(fps * min(0.4, period / 3))))
    run_time = float(active.sum() / fps) if active.any() else seconds
    k = max(1, round(len(peaks) / max(1.0, run_time / period))) if len(peaks) else 1
    idle = float(np.percentile(m, 10))
    suggestion = {
        "period_sec": round(period, 2),
        "returns_per_cycle": int(min(k, 10)),
        "motion_threshold": round(max(0.3, idle + (hi - idle) * 0.25), 1),
        "peak_min_height": round(max(0.5, hi * 0.5), 1),
        "peak_min_distance_sec": round(max(0.1, period / max(1, k) * 0.5), 2),
        "home_exit_threshold": round(float(np.percentile(hd, 80)) * 0.6, 1) if hd.any() else None,
        "home_return_threshold": round(float(np.percentile(hd, 20)) * 1.5 + 0.5, 1) if hd.any() else None,
        "reference_cycle_sec": round(period, 2),
    }
    return suggestion


@router.get("/intervals")
async def intervals(camera_id: int, session: SessionDep, hours: float = 12) -> list[dict]:
    since = datetime.fromtimestamp(time.time() - hours * 3600, UTC)
    rows = (
        await session.execute(
            select(EquipmentInterval)
            .where(
                EquipmentInterval.camera_id == camera_id,
                (EquipmentInterval.end_ts.is_(None)) | (EquipmentInterval.end_ts >= since),
            )
            .order_by(EquipmentInterval.start_ts)
        )
    ).scalars()
    return [
        {"state": r.state, "start": r.start_ts.isoformat(), "end": r.end_ts.isoformat() if r.end_ts else None}
        for r in rows
    ]
