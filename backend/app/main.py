"""api processi: FastAPI REST + WebSocket, frontend build'ini beradi (SPA fallback)."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.cameras import router as cameras_router
from app.api.counting import router as counting_router
from app.api.dataset import router as dataset_router
from app.api.equipment import router as equipment_router
from app.api.health import router as health_router
from app.api.onvif import router as onvif_router
from app.api.products import router as products_router
from app.api.reports import router as reports_router
from app.api.shifts import router as shifts_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.telegram import router as telegram_router
from app.api.training import router as training_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.heartbeat import heartbeat_loop
from app.core.redis import close_redis, get_redis

log = logging.getLogger(__name__)
PROCESS_NAME = "api"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_settings().ensure_data_dirs()
    hb = asyncio.create_task(heartbeat_loop(get_redis(), PROCESS_NAME))
    log.info("API ishga tushdi")
    try:
        yield
    finally:
        hb.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb
        with contextlib.suppress(Exception):
            await get_redis().delete(f"fcv:hb:{PROCESS_NAME}")
        await close_redis()
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="F_CV", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.include_router(health_router, prefix="/api")
    app.include_router(cameras_router, prefix="/api")
    app.include_router(onvif_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    app.include_router(products_router, prefix="/api")
    app.include_router(dataset_router, prefix="/api")
    app.include_router(training_router, prefix="/api")
    app.include_router(counting_router, prefix="/api")
    app.include_router(equipment_router, prefix="/api")
    app.include_router(telegram_router, prefix="/api")
    app.include_router(shifts_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    app.include_router(ws_router)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def api_not_found(path: str) -> JSONResponse:
        return JSONResponse({"detail": "Topilmadi"}, status_code=404)

    _mount_frontend(app, get_settings().frontend_dist)
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Frontend build: statik fayllar + istalgan noma'lum yo'l uchun index.html (SPA fallback)."""
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request) -> FileResponse:  # sync: fayl tekshiruvi threadpool da
        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Frontend build topilmadi: `make build` ni ishga tushiring")
        if path:
            candidate = (dist / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(dist.resolve()):
                return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
