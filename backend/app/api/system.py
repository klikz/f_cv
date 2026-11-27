"""Tizim: resurslar, disk va papkalar hajmi, loglar, muhim hodisalar, zaxira holati, umumiy sozlamalar."""

import asyncio
import json
import os
import re
import shutil
import time
from typing import Any, Literal

import psutil
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep
from app.core import keys
from app.core.config import get_settings
from app.models.cameras import Camera
from app.models.system import SystemEvent
from app.models.tasks import TASK_TYPES, CameraTask
from app.services import autostart, bus
from app.services.images import IMAGES_ROOT_KEY, images_root, resolve_images_root, task_dir
from app.services.settings_store import DEFAULTS, all_settings, set_setting

router = APIRouter(prefix="/system", tags=["system"])
_size_cache: dict[str, Any] = {"ts": 0.0, "data": {}}
_task_size_cache: dict[str, Any] = {"ts": 0.0, "root": None, "data": {}}
HIDDEN_SETTINGS = ("telegram.token", "dataset.autocollect", IMAGES_ROOT_KEY)


def _dir_stats(p) -> tuple[int, int]:
    """(hajm baytda, fayllar soni)."""
    total = n = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
                n += 1
            except OSError:
                pass
    return total, n


def _dir_size(p) -> int:
    return _dir_stats(p)[0]


def _sizes() -> dict:
    if time.time() - _size_cache["ts"] < 120:
        return _size_cache["data"]
    base = get_settings().data_path
    out = {}
    for name in ("images", "snapshots", "datasets", "models", "engines", "logs", "backups", "equipment"):
        p = base / name
        out[name] = _dir_size(p) if p.exists() else 0
    _size_cache.update(ts=time.time(), data=out)
    return out


@router.get("/info")
async def info(redis: RedisDep) -> dict:
    s = get_settings()
    du = shutil.disk_usage(s.data_path)
    vm = psutil.virtual_memory()
    sizes = await asyncio.to_thread(_sizes)
    inf = await redis.hgetall(keys.INFERENCE_STATS)
    video = await redis.hgetall("fcv:video:summary")
    return {
        "disk": {"total": du.total, "used": du.used, "free": du.free, "free_pct": round(du.free / du.total * 100, 1)},
        "folders": sizes,
        "cpu_pct": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(),
        "load": os.getloadavg(),
        "ram": {"total": vm.total, "used": vm.total - vm.available, "pct": vm.percent},
        "inference": inf,
        "video": video,
        "backup": _backup_status(),
    }


def _backup_status() -> dict | None:
    p = get_settings().data_path / "backups" / "last.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


LOG_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) (\w+) \[([^\]]+)\] ([^:]+): (.*)$")


@router.get("/logs")
async def logs(
    level: str = Query("WARNING"), process: str | None = None, limit: int = Query(200, le=2000)
) -> list[dict]:
    """Oxirgi xato/ogohlantirish loglari (barcha processlar log fayllaridan)."""
    order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_l = order.get(level.upper(), 2)
    d = get_settings().data_subdir("logs")

    def read() -> list[dict]:
        out: list[dict] = []
        for f in d.glob("*.log"):
            if process and not f.stem.startswith(process):
                continue
            try:
                with open(f, "rb") as fh:
                    fh.seek(max(0, os.path.getsize(f) - 400_000))
                    lines = fh.read().decode(errors="replace").splitlines()
            except OSError:
                continue
            cur = None
            for ln in lines:
                m = LOG_RE.match(ln)
                if m:
                    if cur:
                        out.append(cur)
                    cur = None
                    if order.get(m.group(2), 1) >= min_l:
                        cur = {
                            "ts": m.group(1),
                            "level": m.group(2),
                            "process": m.group(3),
                            "logger": m.group(4),
                            "message": m.group(5),
                        }
                elif cur is not None and len(cur["message"]) < 4000:
                    cur["message"] += "\n" + ln
            if cur:
                out.append(cur)
        out.sort(key=lambda x: x["ts"], reverse=True)
        return out[:limit]

    return await asyncio.to_thread(read)


@router.get("/events")
async def events(session: SessionDep, limit: int = Query(100, le=1000), kind: str | None = None) -> list[dict]:
    q = select(SystemEvent).order_by(SystemEvent.ts.desc()).limit(limit)
    if kind:
        q = q.where(SystemEvent.kind == kind)
    return [
        {"id": e.id, "ts": e.ts, "level": e.level, "source": e.source, "kind": e.kind, "message": e.message}
        for e in (await session.execute(q)).scalars()
    ]


@router.get("/settings")
async def get_settings_all(session: SessionDep) -> dict:
    s = await all_settings(session)
    for k in HIDDEN_SETTINGS:
        s.pop(k, None)
    return s


class SettingIn(BaseModel):
    value: Any


@router.put("/settings/{key}")
async def put_setting(key: str, data: SettingIn, session: SessionDep) -> dict:
    if key not in DEFAULTS or key in HIDDEN_SETTINGS:
        raise HTTPException(404, "Noma'lum sozlama")
    default = DEFAULTS[key]
    if isinstance(default, dict) and not isinstance(data.value, dict):
        raise HTTPException(422, "Qiymat obyekt bo'lishi kerak")
    await set_setting(session, key, data.value)
    return {"key": key, "value": data.value}


# --- Vazifa rasmlari papkasi ---


class StorageIn(BaseModel):
    images_root: str = ""


def _task_sizes(root, dirs: list) -> dict[str, tuple[int, int]]:
    if _task_size_cache["root"] == str(root) and time.time() - _task_size_cache["ts"] < 60:
        return _task_size_cache["data"]
    out = {d.name: _dir_stats(d) for d in dirs if d.exists()}
    _task_size_cache.update(ts=time.time(), root=str(root), data=out)
    return out


@router.get("/storage")
async def get_storage(session: SessionDep) -> dict:
    """Vazifa rasmlari umumiy papkasi va har bir vazifaning alohida papkasi."""
    value = (await all_settings(session)).get(IMAGES_ROOT_KEY) or ""
    root = await images_root(session)
    cams = (await session.execute(select(Camera.id, Camera.name).order_by(Camera.id))).all()
    enabled = {
        (c, t)
        for c, t, e in (
            await session.execute(select(CameraTask.camera_id, CameraTask.task_type, CameraTask.enabled))
        ).all()
        if e
    }
    rows = [(cid, name, tt, task_dir(root, cid, tt)) for cid, name in cams for tt in TASK_TYPES]
    sizes = await asyncio.to_thread(_task_sizes, root, [r[3] for r in rows])
    du = None
    probe = root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        u = shutil.disk_usage(probe)
        du = {"total": u.total, "free": u.free}
    except OSError:
        pass
    return {
        "images_root": value,
        "resolved": str(root),
        "default": str(resolve_images_root(None)),
        "exists": root.is_dir(),
        "writable": root.is_dir() and os.access(root, os.W_OK),
        "disk": du,
        "layout": "<papka>/cam<kamera>-<vazifa>/",
        "tasks": [
            {
                "camera_id": cid,
                "camera_name": name,
                "task_type": tt,
                "enabled": (cid, tt) in enabled,
                "path": str(d),
                "exists": d.name in sizes,
                "size": sizes.get(d.name, (0, 0))[0],
                "files": sizes.get(d.name, (0, 0))[1],
            }
            for cid, name, tt, d in rows
        ],
    }


@router.put("/storage")
async def put_storage(data: StorageIn, session: SessionDep, redis: RedisDep) -> dict:
    """Umumiy papkani o'zgartirish. Eski rasmlar joyida qoladi (bazada to'liq yo'li saqlangan), yangilari — yangi papkaga."""
    value = data.images_root.strip()
    if "\x00" in value:
        raise HTTPException(422, "Noto'g'ri yo'l")
    root = resolve_images_root(value)
    try:
        await asyncio.to_thread(root.mkdir, parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(422, f"Papkani yaratib bo'lmadi: {e.strerror or e}") from e
    if not root.is_dir() or not os.access(root, os.W_OK):
        raise HTTPException(422, f"Papkaga yozish huquqi yo'q: {root}")
    await set_setting(session, IMAGES_ROOT_KEY, value)
    _task_size_cache["ts"] = 0.0
    await bus.task_changed(redis, 0, None)  # barcha kamera processlari yangi papkani o'qiydi
    return await get_storage(session)


# --- Avtomatik ishga tushish (Ubuntu 26.04: systemd, GNOME autostart, GDM) ---


class AutostartIn(BaseModel):
    enabled: bool
    browser: str | None = None
    fullscreen: bool = True


@router.get("/autostart")
async def get_autostart() -> dict:
    return await autostart.status()


@router.put("/autostart/{item}")
async def put_autostart(item: Literal["services", "kiosk", "autologin"], data: AutostartIn) -> dict:
    try:
        if item == "kiosk":
            if data.enabled:
                browsers = autostart.available_browsers()
                if not browsers:
                    raise autostart.AutostartError("Brauzer topilmadi (google-chrome, chromium yoki firefox o'rnating)")
                await asyncio.to_thread(autostart.write_desktop, data.browser or next(iter(browsers)), data.fullscreen)
            else:
                await asyncio.to_thread(autostart.remove_desktop)
        else:
            await autostart.run_helper(item, data.enabled)
    except autostart.AutostartError as e:
        raise HTTPException(409, str(e)) from e
    except OSError as e:
        raise HTTPException(500, f"Faylni yozib bo'lmadi: {e}") from e
    return await autostart.status()
