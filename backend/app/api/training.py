"""Train navbati va model registri."""

import json
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.api.deps import RedisDep, SessionDep, not_found
from app.core import keys
from app.core.config import get_settings
from app.models.catalog import ModelVersion, Product, TrainingJob, TrainingMetric
from app.services import bus
from app.services.settings_store import get_setting

router = APIRouter(tags=["training"])


class JobCreate(BaseModel):
    product_ids: list[int] = Field(min_length=1)
    camera_id: int | None = None
    kind: Literal["full", "draft"] = "full"
    model_size: Literal["n", "s"] | None = None
    epochs: int | None = Field(None, ge=1, le=500)
    imgsz: int | None = Field(None, ge=320, le=1280)
    batch: int | None = Field(None, ge=1, le=128)
    negative_ratio: float | None = Field(None, ge=0, le=10)
    scheduled_at: datetime | None = None


class AutolabelIn(BaseModel):
    product_id: int
    conf: float = Field(0.4, ge=0.05, le=0.95)
    image_ids: list[int] | None = None
    camera_id: int | None = None
    limit: int = Field(2000, ge=1, le=20000)


class MetricOut(BaseModel):
    epoch: int
    box_loss: float | None
    cls_loss: float | None
    dfl_loss: float | None
    precision: float | None
    recall: float | None
    map50: float | None
    map5095: float | None


class JobOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None
    camera_id: int | None
    kind: str
    params: dict[str, Any]
    status: str
    stage: str
    epoch: int
    epochs: int
    scheduled_at: datetime | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    eta_sec: float | None
    error: str | None
    model_version_id: int | None
    stats: dict[str, Any]


class JobDetail(JobOut):
    metrics: list[MetricOut] = []


def _job_out(j: TrainingJob, names: dict[int, str]) -> dict:
    return dict(
        id=j.id,
        product_id=j.product_id,
        product_name=names.get(j.product_id),
        camera_id=j.camera_id,
        kind=j.kind,
        params=j.params or {},
        status=j.status,
        stage=j.stage,
        epoch=j.epoch,
        epochs=j.epochs,
        scheduled_at=j.scheduled_at,
        created_at=j.created_at,
        started_at=j.started_at,
        finished_at=j.finished_at,
        eta_sec=j.eta_sec,
        error=j.error,
        model_version_id=j.model_version_id,
        stats=j.stats or {},
    )


async def _names(session) -> dict[int, str]:
    return dict((await session.execute(select(Product.id, Product.name))).all())


@router.get("/training/jobs", response_model=list[JobOut])
async def list_jobs(session: SessionDep, limit: int = Query(200, le=1000), status: str | None = None) -> list[JobOut]:
    q = select(TrainingJob).order_by(TrainingJob.id.desc()).limit(limit)
    if status:
        q = q.where(TrainingJob.status == status)
    names = await _names(session)
    return [JobOut(**_job_out(j, names)) for j in (await session.execute(q)).scalars()]


@router.get("/training/jobs/{job_id}", response_model=JobDetail)
async def get_job(job_id: int, session: SessionDep) -> JobDetail:
    j = await session.get(TrainingJob, job_id)
    if j is None:
        raise not_found("Train topilmadi")
    ms = (
        await session.execute(
            select(TrainingMetric).where(TrainingMetric.job_id == job_id).order_by(TrainingMetric.epoch)
        )
    ).scalars()
    return JobDetail(
        **_job_out(j, await _names(session)), metrics=[MetricOut.model_validate(m, from_attributes=True) for m in ms]
    )


@router.get("/training/jobs/{job_id}/log")
async def job_log(job_id: int, tail: int = Query(300, le=5000)) -> dict:
    p = get_settings().data_subdir("logs") / "train" / f"{job_id}.log"
    if not p.exists():
        return {"lines": []}
    lines = p.read_text(errors="replace").splitlines()
    # ultralytics jarayon chizig'i (\r) — oxirgi holatni qoldirish
    lines = [ln.split("\r")[-1] for ln in lines if ln.strip()]
    return {"lines": lines[-tail:]}


@router.post("/training/jobs", response_model=list[JobOut], status_code=201)
async def create_jobs(data: JobCreate, session: SessionDep, redis: RedisDep) -> list[JobOut]:
    defaults = await get_setting(session, "training.defaults")
    params = {k: v for k, v in defaults.items()}
    for k in ("model_size", "epochs", "imgsz", "batch", "negative_ratio"):
        v = getattr(data, k)
        if v is not None:
            params[k] = v
    if data.kind == "draft":
        params["epochs"] = min(params.get("epochs", 15), 15)
    out = []
    for pid in data.product_ids:
        if await session.get(Product, pid) is None:
            raise not_found(f"Mahsulot #{pid} topilmadi")
        j = TrainingJob(
            product_id=pid,
            camera_id=data.camera_id,
            kind=data.kind,
            params=params,
            scheduled_at=data.scheduled_at,
            status="queued",
            stage="queued",
            epochs=int(params.get("epochs", 0)),
        )
        session.add(j)
        out.append(j)
    await session.commit()
    names = await _names(session)
    await bus.emit_event(redis, "train_queued", {"job_ids": [j.id for j in out]})
    return [JobOut(**_job_out(j, names)) for j in out]


@router.post("/dataset/autolabel", response_model=JobOut, status_code=201)
async def autolabel(data: AutolabelIn, session: SessionDep) -> JobOut:
    if await session.get(Product, data.product_id) is None:
        raise not_found("Mahsulot topilmadi")
    has_model = (
        await session.execute(
            select(ModelVersion.id)
            .where(ModelVersion.product_id == data.product_id, ModelVersion.status == "ready")
            .limit(1)
        )
    ).scalar_one_or_none()
    if not has_model:
        raise HTTPException(422, "Bu mahsulot uchun model yo'q — avval ~30 rasmni belgilab, tez qoralama train qiling")
    j = TrainingJob(
        product_id=data.product_id,
        kind="autolabel",
        params=data.model_dump(exclude={"product_id"}),
        status="queued",
        stage="queued",
    )
    session.add(j)
    await session.commit()
    return JobOut(**_job_out(j, await _names(session)))


@router.post("/training/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: int, session: SessionDep, redis: RedisDep) -> JobOut:
    j = await session.get(TrainingJob, job_id)
    if j is None:
        raise not_found("Train topilmadi")
    if j.status == "queued":
        j.status = "cancelled"
        await session.commit()
    elif j.status == "running":
        await redis.set(keys.TRAIN_CANCEL, str(job_id), ex=600)
        j.status = "cancelling"
        await session.commit()
    else:
        raise HTTPException(409, "Bu train allaqachon tugagan")
    return JobOut(**_job_out(j, await _names(session)))


@router.post("/training/jobs/{job_id}/retry", response_model=JobOut, status_code=201)
async def retry_job(job_id: int, session: SessionDep, resume: bool = False) -> JobOut:
    """Xato/bekor qilingan train'ni qayta boshlash yoki oxirgi saqlangan epoch'dan davom ettirish."""
    j = await session.get(TrainingJob, job_id)
    if j is None:
        raise not_found("Train topilmadi")
    params = dict(j.params or {})
    if resume:
        last = get_settings().data_subdir("models") / "runs" / str(job_id) / "run" / "weights" / "last.pt"
        if not last.exists():
            raise HTTPException(422, "Davom ettirish uchun saqlangan epoch topilmadi — qayta boshlang")
        params["resume_from"] = str(last)
    nj = TrainingJob(
        product_id=j.product_id,
        camera_id=j.camera_id,
        kind=j.kind,
        params=params,
        status="queued",
        stage="queued",
        epochs=j.epochs,
    )
    session.add(nj)
    await session.commit()
    return JobOut(**_job_out(nj, await _names(session)))


@router.get("/training/current")
async def current(redis: RedisDep) -> dict:
    d = await redis.hgetall(keys.TRAIN_CURRENT)
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            out[k] = json.loads(v)
        except (ValueError, TypeError):
            out[k] = v
    out["inference_paused"] = await redis.get(keys.INFERENCE_PAUSED)
    return out


# ---------- model registri ----------
class VersionOut(BaseModel):
    id: int
    product_id: int
    camera_id: int | None
    version: int
    model_size: str
    is_draft: bool
    metrics: dict[str, Any]
    engine_ready: bool
    trt_version: str | None
    driver_version: str | None
    status: str
    is_active: bool
    job_id: int | None
    created_at: datetime


class ProductModels(BaseModel):
    product_id: int
    code: str
    name: str
    active: VersionOut | None
    latest: VersionOut | None
    versions_count: int


def _v(m: ModelVersion) -> VersionOut:
    return VersionOut(
        id=m.id,
        product_id=m.product_id,
        camera_id=m.camera_id,
        version=m.version,
        model_size=m.model_size,
        is_draft=m.is_draft,
        metrics=m.metrics or {},
        engine_ready=bool(m.engine_path) and m.status == "ready",
        trt_version=m.trt_version,
        driver_version=m.driver_version,
        status=m.status,
        is_active=m.is_active,
        job_id=m.job_id,
        created_at=m.created_at,
    )


@router.get("/models", response_model=list[ProductModels])
async def models_overview(session: SessionDep) -> list[ProductModels]:
    prods = (await session.execute(select(Product).order_by(Product.name))).scalars().all()
    vs = (await session.execute(select(ModelVersion).order_by(ModelVersion.version.desc()))).scalars().all()
    by: dict[int, list[ModelVersion]] = {}
    for v in vs:
        by.setdefault(v.product_id, []).append(v)
    out = []
    for p in prods:
        lst = by.get(p.id, [])
        act = next((v for v in lst if v.is_active), None)
        out.append(
            ProductModels(
                product_id=p.id,
                code=p.code,
                name=p.name,
                active=_v(act) if act else None,
                latest=_v(lst[0]) if lst else None,
                versions_count=len(lst),
            )
        )
    return out


@router.get("/models/{product_id}", response_model=list[VersionOut])
async def product_versions(product_id: int, session: SessionDep) -> list[VersionOut]:
    vs = (
        await session.execute(
            select(ModelVersion).where(ModelVersion.product_id == product_id).order_by(ModelVersion.version.desc())
        )
    ).scalars()
    return [_v(v) for v in vs]


@router.post("/models/versions/{version_id}/activate", response_model=VersionOut)
async def activate(version_id: int, session: SessionDep, redis: RedisDep) -> VersionOut:
    mv = await session.get(ModelVersion, version_id)
    if mv is None:
        raise not_found("Versiya topilmadi")
    if mv.is_draft or mv.status != "ready" or not mv.engine_path:
        raise HTTPException(422, "Faqat tayyor (engine qurilgan) to'liq versiyani faollashtirish mumkin")
    same_scope = ModelVersion.camera_id.is_(None) if mv.camera_id is None else ModelVersion.camera_id == mv.camera_id
    await session.execute(
        update(ModelVersion).where(ModelVersion.product_id == mv.product_id, same_scope).values(is_active=False)
    )
    mv.is_active = True
    await session.commit()
    await bus.publish(redis, keys.CH_SYSTEM, {"cmd": "models_changed", "product_id": mv.product_id})
    await bus.task_changed(redis, 0, "counting")
    return _v(mv)


@router.post("/models/{product_id}/rollback", response_model=VersionOut)
async def rollback(product_id: int, session: SessionDep, redis: RedisDep) -> VersionOut:
    vs = (
        (
            await session.execute(
                select(ModelVersion)
                .where(
                    ModelVersion.product_id == product_id,
                    ModelVersion.is_draft.is_(False),
                    ModelVersion.status == "ready",
                )
                .order_by(ModelVersion.version.desc())
            )
        )
        .scalars()
        .all()
    )
    act = next((i for i, v in enumerate(vs) if v.is_active), None)
    if act is None or act + 1 >= len(vs):
        raise HTTPException(422, "Qaytish uchun oldingi versiya yo'q")
    return await activate(vs[act + 1].id, session, redis)


@router.delete("/models/versions/{version_id}", status_code=204)
async def delete_version(version_id: int, session: SessionDep) -> Response:
    mv = await session.get(ModelVersion, version_id)
    if mv is None:
        raise not_found("Versiya topilmadi")
    if mv.is_active:
        raise HTTPException(409, "Faol versiyani o'chirib bo'lmaydi — avval boshqasini faollashtiring")
    await session.delete(mv)
    await session.commit()
    return Response(status_code=204)
