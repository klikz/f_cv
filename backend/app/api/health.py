"""/api/health — DB, Redis, GPU, disk va processlar holati."""

import asyncio
import logging
import shutil
import time
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.heartbeat import EXPECTED_PROCESSES, read_heartbeats
from app.core.redis import get_redis

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

Status = Literal["ok", "warn", "error"]


class Check(BaseModel):
    status: Status
    detail: str | None = None
    data: dict[str, Any] = {}


class ProcessStatus(BaseModel):
    name: str
    status: Status
    pid: int | None = None
    age_sec: float | None = None


class Health(BaseModel):
    status: Status
    server_time: datetime
    timezone: str
    db: Check
    redis: Check
    gpu: Check
    disk: Check
    processes: list[ProcessStatus]


async def _check_db() -> Check:
    try:
        async with asyncio.timeout(3):
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        return Check(status="ok")
    except Exception as e:
        return Check(status="error", detail=f"PostgreSQL ga ulanib bo'lmadi: {e.__class__.__name__}")


async def _check_redis() -> tuple[Check, dict[str, dict[str, Any]] | None]:
    try:
        async with asyncio.timeout(3):
            r = get_redis()
            await r.ping()
            hbs = await read_heartbeats(r)
        return Check(status="ok"), hbs
    except Exception as e:
        return Check(status="error", detail=f"Redis ga ulanib bo'lmadi: {e.__class__.__name__}"), None


def _gpu_sync() -> Check:
    try:
        import pynvml

        pynvml.nvmlInit()
        try:
            gpus = []
            for i in range(pynvml.nvmlDeviceGetCount()):
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                util = pynvml.nvmlDeviceGetUtilizationRates(h)
                name = pynvml.nvmlDeviceGetName(h)
                gpus.append(
                    {
                        "index": i,
                        "name": name.decode() if isinstance(name, bytes) else name,
                        "util_pct": util.gpu,
                        "mem_used_mb": mem.used // 2**20,
                        "mem_total_mb": mem.total // 2**20,
                        "temp_c": pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU),
                    }
                )
            driver = pynvml.nvmlSystemGetDriverVersion()
            driver = driver.decode() if isinstance(driver, bytes) else driver
        finally:
            pynvml.nvmlShutdown()
        if not gpus:
            return Check(status="error", detail="GPU topilmadi")
        hot = any(g["temp_c"] >= 85 for g in gpus)
        return Check(
            status="warn" if hot else "ok",
            detail="GPU harorati yuqori" if hot else None,
            data={"driver": driver, "gpus": gpus},
        )
    except Exception as e:
        return Check(status="error", detail=f"GPU holatini o'qib bo'lmadi: {e.__class__.__name__}")


def _disk_sync() -> Check:
    path = get_settings().data_path
    try:
        u = shutil.disk_usage(path if path.exists() else path.parent)
    except OSError as e:
        return Check(status="error", detail=f"Diskni o'qib bo'lmadi: {e}")
    free_pct = u.free / u.total * 100
    status: Status = "ok" if free_pct >= 10 else ("warn" if free_pct >= 3 else "error")
    return Check(
        status=status,
        detail=None if status == "ok" else f"Diskda joy kam: {free_pct:.1f}% bo'sh",
        data={
            "path": str(path),
            "total_gb": round(u.total / 2**30, 1),
            "used_gb": round(u.used / 2**30, 1),
            "free_gb": round(u.free / 2**30, 1),
            "free_pct": round(free_pct, 1),
        },
    )


def _processes(hbs: dict[str, dict[str, Any]] | None) -> list[ProcessStatus]:
    now = time.time()
    ttl = get_settings().heartbeat_ttl_sec
    names = list(EXPECTED_PROCESSES)
    if hbs:
        names += sorted(n for n in hbs if n not in EXPECTED_PROCESSES)
    out: list[ProcessStatus] = []
    for n in names:
        hb = (hbs or {}).get(n)
        if hb is None:
            out.append(ProcessStatus(name=n, status="error"))
            continue
        age = max(0.0, now - hb["ts"])
        out.append(ProcessStatus(name=n, status="ok" if age <= ttl else "warn", pid=hb["pid"], age_sec=round(age, 1)))
    return out


def _worst(*statuses: Status) -> Status:
    if "error" in statuses:
        return "error"
    return "warn" if "warn" in statuses else "ok"


@router.get("/health", response_model=Health)
async def health() -> Health:
    (db, (redis, hbs), gpu, disk) = await asyncio.gather(
        _check_db(), _check_redis(), asyncio.to_thread(_gpu_sync), asyncio.to_thread(_disk_sync)
    )
    procs = _processes(hbs)
    s = get_settings()
    return Health(
        status=_worst(db.status, redis.status, gpu.status, disk.status, *(p.status for p in procs)),
        server_time=datetime.now(UTC),
        timezone=s.timezone,
        db=db,
        redis=redis,
        gpu=gpu,
        disk=disk,
        processes=procs,
    )
