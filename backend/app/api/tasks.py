"""Kamera vazifalari: yoqish/o'chirish, sanash va uskuna sozlamalari, tahlil oqimi."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep, not_found
from app.models.cameras import Camera
from app.models.tasks import TASK_TYPES, CameraTask, CountingConfig, EquipmentConfig
from app.schemas.tasks import AnalysisStreamIn, CountingConfigIO, EquipmentConfigIO, TasksOut, TaskState, TaskToggle
from app.services import bus

router = APIRouter(prefix="/cameras/{camera_id}", tags=["tasks"])


async def _cam(session, camera_id: int) -> Camera:
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise not_found("Kamera topilmadi")
    return cam


def _counting_issues(c: CountingConfig | None, cam: Camera) -> list[str]:
    if c is None or not c.roi_polygon:
        return ["ROI hududi chizilmagan"]
    out = []
    if not c.line:
        out.append("Kesib o'tish chizig'i chizilmagan")
    if c.stream != cam.analysis_stream:
        out.append("Shakllar boshqa oqimga chizilgan — qayta chizing")
    return out


def _equipment_issues(e: EquipmentConfig | None, cam: Camera) -> list[str]:
    if e is None or not e.roi_polygon:
        return ["ROI hududi chizilmagan"]
    out = []
    if e.stream != cam.analysis_stream:
        out.append("Shakllar boshqa oqimga chizilgan — qayta chizing")
    if e.cycle_mode == "home" and not e.home_reference:
        out.append("Tayanch kadr olinmagan (sikllar sanalmaydi)")
    return out


@router.get("/tasks", response_model=TasksOut)
async def get_tasks(camera_id: int, session: SessionDep) -> TasksOut:
    cam = await _cam(session, camera_id)
    rows = {
        t.task_type: t
        for t in (await session.execute(select(CameraTask).where(CameraTask.camera_id == camera_id))).scalars()
    }
    c = await session.get(CountingConfig, camera_id)
    e = await session.get(EquipmentConfig, camera_id)
    sizes = {s.kind: ([s.width, s.height] if s.width else None) for s in cam.streams}
    ci, ei = _counting_issues(c, cam), _equipment_issues(e, cam)
    return TasksOut(
        camera_id=camera_id,
        analysis_stream=cam.analysis_stream,  # type: ignore[arg-type]
        has_sub=bool(cam.sub_rtsp_url),
        stream_sizes={"main": sizes.get("main"), "sub": sizes.get("sub") if cam.sub_rtsp_url else None},
        tasks={
            "counting": TaskState(
                enabled=bool(rows.get("counting") and rows["counting"].enabled),
                configured=not any("chizilmagan" in i or "qayta" in i for i in ci),
                issues=ci,
            ),
            "equipment": TaskState(
                enabled=bool(rows.get("equipment") and rows["equipment"].enabled),
                configured=not any("chizilmagan" in i or "qayta" in i for i in ei),
                issues=ei,
            ),
        },
    )


@router.put("/tasks/{task_type}", response_model=TasksOut)
async def toggle_task(
    camera_id: int, task_type: str, data: TaskToggle, session: SessionDep, redis: RedisDep
) -> TasksOut:
    if task_type not in TASK_TYPES:
        raise HTTPException(404, "Noma'lum vazifa")
    await _cam(session, camera_id)
    row = (
        await session.execute(
            select(CameraTask).where(CameraTask.camera_id == camera_id, CameraTask.task_type == task_type)
        )
    ).scalar_one_or_none()
    if row is None:
        row = CameraTask(camera_id=camera_id, task_type=task_type, enabled=data.enabled)
        session.add(row)
    else:
        row.enabled = data.enabled
    await session.commit()
    await bus.task_changed(redis, camera_id, task_type)
    return await get_tasks(camera_id, session)


@router.post("/analysis-stream", response_model=TasksOut)
async def set_analysis_stream(camera_id: int, data: AnalysisStreamIn, session: SessionDep, redis: RedisDep) -> TasksOut:
    """Tahlil oqimini almashtirish: shakllar boshqa oqim kadriga chizilgani uchun tozalanadi."""
    cam = await _cam(session, camera_id)
    if data.stream == "sub" and not cam.sub_rtsp_url:
        raise HTTPException(422, "Bu kamerada sub oqim yo'q")
    if cam.analysis_stream != data.stream:
        cam.analysis_stream = data.stream
        c = await session.get(CountingConfig, camera_id)
        e = await session.get(EquipmentConfig, camera_id)
        if data.keep_shapes:
            for cfg in (c, e):
                if cfg is not None:
                    cfg.stream = data.stream
        else:
            if c is not None:
                c.roi_polygon, c.line, c.stream = None, None, data.stream
            if e is not None:
                e.roi_polygon, e.control_zone, e.exclude_zones, e.home_reference, e.stream = (
                    None,
                    None,
                    [],
                    None,
                    data.stream,
                )
        await session.commit()
        await bus.task_changed(redis, camera_id, None)
        await bus.camera_changed(redis, "updated", camera_id)
    return await get_tasks(camera_id, session)


@router.get("/counting", response_model=CountingConfigIO)
async def get_counting(camera_id: int, session: SessionDep) -> CountingConfigIO:
    cam = await _cam(session, camera_id)
    c = await session.get(CountingConfig, camera_id)
    if c is None:
        return CountingConfigIO(stream=cam.analysis_stream)  # type: ignore[arg-type]
    return CountingConfigIO.model_validate(c, from_attributes=True)


@router.put("/counting", response_model=CountingConfigIO)
async def put_counting(
    camera_id: int, data: CountingConfigIO, session: SessionDep, redis: RedisDep
) -> CountingConfigIO:
    cam = await _cam(session, camera_id)
    c = await session.get(CountingConfig, camera_id)
    if c is None:
        c = CountingConfig(camera_id=camera_id)
        session.add(c)
    vals = data.model_dump()
    vals["stream"] = cam.analysis_stream  # koordinatalar doim joriy tahlil oqimi kadriga nisbatan
    for k, v in vals.items():
        setattr(c, k, [list(p) for p in v] if k in ("roi_polygon", "line") and v else v)
    await session.commit()
    await bus.task_changed(redis, camera_id, "counting")
    return CountingConfigIO.model_validate(c, from_attributes=True)


@router.get("/equipment", response_model=EquipmentConfigIO)
async def get_equipment(camera_id: int, session: SessionDep) -> EquipmentConfigIO:
    cam = await _cam(session, camera_id)
    e = await session.get(EquipmentConfig, camera_id)
    if e is None:
        return EquipmentConfigIO(stream=cam.analysis_stream)  # type: ignore[arg-type]
    return EquipmentConfigIO.model_validate(e, from_attributes=True)


@router.put("/equipment", response_model=EquipmentConfigIO)
async def put_equipment(
    camera_id: int, data: EquipmentConfigIO, session: SessionDep, redis: RedisDep
) -> EquipmentConfigIO:
    cam = await _cam(session, camera_id)
    e = await session.get(EquipmentConfig, camera_id)
    if e is None:
        e = EquipmentConfig(camera_id=camera_id)
        session.add(e)
    vals = data.model_dump(exclude={"home_reference"})
    vals["stream"] = cam.analysis_stream
    for k, v in vals.items():
        if k in ("roi_polygon", "control_zone") and v:
            v = [list(p) for p in v]
        elif k == "exclude_zones":
            v = [[list(p) for p in z] for z in v]
        setattr(e, k, v)
    await session.commit()
    await bus.task_changed(redis, camera_id, "equipment")
    return EquipmentConfigIO.model_validate(e, from_attributes=True)
