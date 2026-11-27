"""Trainer: train navbati (bir vaqtda bitta job), dataset → train → validatsiya → TensorRT eksport.

- Navbat ishlayotganda mahsulot inference to'xtatiladi (`fcv:inference:paused`), oraliq `coverage_gaps` ga
  yoziladi (sabab: train); navbat bo'shagach inference avtomatik yoqiladi.
- Job turlari: `full` (train + eksport), `draft` (tez qoralama, eksportsiz — avto-belgilash uchun),
  `autolabel` (modeldan ramka takliflari).
- Servis yiqilsa/elektr o'chsa: ishga tushganda "running" job'lar "failed" bo'ladi (davom ettirish mumkin),
  yarim qurilgan engine'lar o'chiriladi, inference bayrog'i olinadi.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from app.core import keys
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models.cameras import CoverageGap
from app.models.catalog import Annotation, DatasetImage, ModelVersion, Product, TrainingJob, TrainingMetric
from app.models.tasks import CameraTask
from app.services import bus
from app.services.images import roi_crop_box
from training.ml_env import setup_ultralytics_env
from training.prepare import build_dataset, crop_boxes

log = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]


def now() -> datetime:
    return datetime.now(UTC)


class Cancelled(Exception):
    pass


class TrainerService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.s = get_settings()
        self.sync_engine = create_engine(self.s.database_url.replace("+asyncpg", "+psycopg"), pool_pre_ping=True)
        self.proc: asyncio.subprocess.Process | None = None
        self.current: int | None = None
        self.gap_ids: list[int] = []
        self.env = {**os.environ, **setup_ultralytics_env(), "PYTHONUNBUFFERED": "1"}

    # ---------- tiklanish ----------
    async def recover(self) -> None:
        async with get_sessionmaker()() as s:
            stuck = (
                (await s.execute(select(TrainingJob).where(TrainingJob.status.in_(["running", "cancelling"]))))
                .scalars()
                .all()
            )
            for j in stuck:
                j.status = "failed"
                j.finished_at = now()
                j.error = "Servis to'xtab qoldi (elektr o'chishi yoki qayta ishga tushish). Davom ettirish yoki qayta boshlash mumkin."
                log.warning("Job %s to'xtab qolgan — 'failed' qilindi", j.id)
            building = (await s.execute(select(ModelVersion).where(ModelVersion.status == "building"))).scalars().all()
            for mv in building:
                mv.status = "failed"
            await s.execute(
                update(CoverageGap)
                .where(CoverageGap.reason == "train", CoverageGap.end_ts.is_(None))
                .values(end_ts=now())
            )
            await s.commit()
        # yarim qurilgan engine'lar
        for p in self.s.data_subdir("engines").rglob("*.building"):
            with contextlib.suppress(OSError):
                p.unlink()
                log.info("Yarim qurilgan engine o'chirildi: %s", p)
        await self.redis.delete(keys.INFERENCE_PAUSED, keys.TRAIN_CURRENT, keys.TRAIN_CANCEL)
        await self.check_engines()

    async def check_engines(self) -> None:
        """Drayver/TensorRT o'zgargan bo'lsa engine yaroqsiz — saqlangan .pt dan qayta qurish navbatga (8.2)."""
        from training.ml_env import versions

        cur = versions()
        async with get_sessionmaker()() as s:
            vs = (
                (
                    await s.execute(
                        select(ModelVersion).where(
                            ModelVersion.is_draft.is_(False),
                            ModelVersion.status.in_(["ready", "stale"]),
                            ModelVersion.engine_path.isnot(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            queued = set(
                (
                    await s.execute(
                        select(TrainingJob.model_version_id).where(
                            TrainingJob.kind == "rebuild", TrainingJob.status.in_(["queued", "running"])
                        )
                    )
                ).scalars()
            )
            for mv in vs:
                engine_missing = not (self.s.data_path / mv.engine_path).exists()
                mismatch = (mv.trt_version and cur.get("trt") and mv.trt_version != cur["trt"]) or (
                    mv.driver_version
                    and cur.get("driver")
                    and mv.driver_version.split(".")[0] != cur["driver"].split(".")[0]
                )
                if (engine_missing or mismatch) and mv.id not in queued:
                    mv.status = "stale"
                    s.add(
                        TrainingJob(
                            product_id=mv.product_id,
                            camera_id=mv.camera_id,
                            kind="rebuild",
                            params={"version_id": mv.id},
                            status="queued",
                            stage="queued",
                            model_version_id=mv.id,
                        )
                    )
                    log.warning(
                        "Engine qayta qurish navbatga: mahsulot %s v%s (%s)",
                        mv.product_id,
                        mv.version,
                        "fayl yo'q" if engine_missing else f"TRT {mv.trt_version}→{cur.get('trt')}",
                    )
            await s.commit()

    async def rebuild(self, job: TrainingJob) -> None:
        async with get_sessionmaker()() as s:
            mv = await s.get(ModelVersion, (job.params or {}).get("version_id") or job.model_version_id)
        if mv is None:
            raise RuntimeError("Versiya topilmadi")
        await self.set_job(job.id, stage="export")
        exp: dict = {}

        async def on_exp(text: str) -> None:
            nonlocal exp
            if text.startswith("FCV_EXPORT "):
                exp = json.loads(text[11:])
            elif text.startswith("FCV_ERROR "):
                raise RuntimeError(json.loads(text[10:])["error"])

        out = self.s.data_path / (mv.engine_path or f"engines/{mv.product_id}/v{mv.version}/model.engine")
        rc = await self.run_sub(
            job.id,
            ["training.run_export", "--pt", str(self.s.data_path / mv.pt_path), "--engine-out", str(out)],
            on_exp,
        )
        if rc != 0 or not exp.get("engine"):
            raise RuntimeError("Engine qayta qurilmadi")
        async with get_sessionmaker()() as s:
            await s.execute(
                update(ModelVersion)
                .where(ModelVersion.id == mv.id)
                .values(
                    status="ready",
                    trt_version=exp.get("trt"),
                    driver_version=exp.get("driver"),
                    engine_path=str(out.relative_to(self.s.data_path)),
                )
            )
            await s.commit()
        await bus.task_changed(self.redis, 0, "counting")

    # ---------- navbat ----------
    async def next_job(self) -> TrainingJob | None:
        async with get_sessionmaker()() as s:
            return (
                await s.execute(
                    select(TrainingJob)
                    .where(
                        TrainingJob.status == "queued",
                        (TrainingJob.scheduled_at.is_(None)) | (TrainingJob.scheduled_at <= now()),
                    )
                    .order_by(TrainingJob.id)
                    .limit(1)
                )
            ).scalar_one_or_none()

    async def pause_inference(self, reason: str) -> None:
        if await self.redis.exists(keys.INFERENCE_PAUSED):
            return
        await self.redis.set(keys.INFERENCE_PAUSED, reason)
        await bus.publish(self.redis, keys.CH_SYSTEM, {"cmd": "inference_paused", "reason": reason})
        async with get_sessionmaker()() as s:
            cams = (
                (
                    await s.execute(
                        select(CameraTask.camera_id).where(
                            CameraTask.task_type == "counting", CameraTask.enabled.is_(True)
                        )
                    )
                )
                .scalars()
                .all()
            )
            self.gap_ids = []
            for cid in cams:
                g = CoverageGap(camera_id=cid, task_type="counting", reason="train", start_ts=now(), detail=reason)
                s.add(g)
                await s.flush()
                self.gap_ids.append(g.id)
            await s.commit()
        log.info("Inference to'xtatildi (%s)", reason)

    async def resume_inference(self) -> None:
        if not await self.redis.exists(keys.INFERENCE_PAUSED):
            return
        await self.redis.delete(keys.INFERENCE_PAUSED)
        await bus.publish(self.redis, keys.CH_SYSTEM, {"cmd": "inference_resumed"})
        async with get_sessionmaker()() as s:
            await s.execute(
                update(CoverageGap)
                .where(CoverageGap.reason == "train", CoverageGap.end_ts.is_(None))
                .values(end_ts=now())
            )
            await s.commit()
        log.info("Inference qayta yoqildi")

    async def run(self, stop: asyncio.Event) -> None:
        await self.recover()
        while not stop.is_set():
            job = await self.next_job()
            if job is None:
                await self.resume_inference()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), 2.0)
                continue
            if job.kind in ("full", "draft", "rebuild"):
                await self.pause_inference(f"Train: job #{job.id}")
            await self.execute(job)

    # ---------- job ----------
    async def set_job(self, job_id: int, **vals: Any) -> None:
        async with get_sessionmaker()() as s:
            await s.execute(update(TrainingJob).where(TrainingJob.id == job_id).values(**vals))
            await s.commit()
        live = {
            k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in vals.items()
            if k in ("stage", "status", "epoch", "epochs", "eta_sec", "error")
        }
        if live:
            await self.redis.hset(
                keys.TRAIN_CURRENT, mapping={"job_id": job_id, **{k: json.dumps(v) for k, v in live.items()}}
            )
            await bus.emit_event(self.redis, "train_progress", {"job_id": job_id, **live})

    async def check_cancel(self, job_id: int) -> None:
        if await self.redis.get(keys.TRAIN_CANCEL) == str(job_id):
            raise Cancelled()

    def log_path(self, job_id: int) -> Path:
        p = self.s.data_subdir("logs") / "train" / f"{job_id}.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    async def run_sub(self, job_id: int, args: list[str], on_line, stdin: bytes | None = None) -> int:
        logf = open(self.log_path(job_id), "a", encoding="utf-8")  # noqa: SIM115
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            *args,
            cwd=str(BACKEND_DIR),
            env=self.env,
            stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if stdin is not None:
            assert self.proc.stdin
            self.proc.stdin.write(stdin)
            await self.proc.stdin.drain()
            self.proc.stdin.close()
        assert self.proc.stdout
        try:
            while True:
                try:
                    line = await asyncio.wait_for(self.proc.stdout.readline(), 1.0)
                except TimeoutError:
                    await self.check_cancel(job_id)
                    continue
                if not line:
                    break
                text = line.decode(errors="replace").rstrip()
                logf.write(text + "\n")
                logf.flush()
                await on_line(text)
                await self.check_cancel(job_id)
            return await self.proc.wait()
        except Cancelled:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 10)
            except TimeoutError:
                self.proc.kill()
            raise
        finally:
            logf.close()
            self.proc = None

    async def execute(self, job: TrainingJob) -> None:
        jid = job.id
        self.current = jid
        t0 = time.time()
        await self.set_job(jid, status="running", stage="dataset", started_at=now(), error=None, epoch=0)
        await self.redis.hset(
            keys.TRAIN_CURRENT,
            mapping={"job_id": jid, "product_id": job.product_id, "kind": job.kind, "started": time.time()},
        )
        try:
            if job.kind == "rebuild":
                await self.rebuild(job)
                await self.set_job(jid, status="done", stage="done", finished_at=now())
            elif job.kind == "autolabel":
                await self.autolabel(job)
                await self.set_job(
                    jid,
                    status="done",
                    stage="done",
                    finished_at=now(),
                    stats={**(job.stats or {}), "seconds": time.time() - t0},
                )
            else:
                await self.train(job, t0)
        except Cancelled:
            await self.set_job(jid, status="cancelled", finished_at=now(), error="Foydalanuvchi bekor qildi")
            await bus.emit_event(self.redis, "train_cancelled", {"job_id": jid}, durable=False)
        except Exception as e:
            log.exception("Job %s xato", jid)
            await self.set_job(jid, status="failed", finished_at=now(), error=str(e)[:2000])
            await self._emit_done(job, ok=False, error=str(e))
        finally:
            self.current = None
            await self.redis.delete(keys.TRAIN_CURRENT, keys.TRAIN_CANCEL)

    async def _emit_done(self, job: TrainingJob, ok: bool, **extra: Any) -> None:
        async with get_sessionmaker()() as s:
            p = await s.get(Product, job.product_id)
        from app.services.system_events import record_sync

        await asyncio.to_thread(
            record_sync,
            "train_done" if ok else "train_failed",
            f"Train #{job.id} ({p.name if p else '?'}) {'tugadi' if ok else 'xato: ' + str(extra.get('error', ''))[:200]}",
            level="info" if ok else "error",
            source="trainer",
            data={"job_id": job.id},
        )
        async with get_sessionmaker()() as s:
            p = await s.get(Product, job.product_id)
        await bus.emit_event(
            self.redis,
            "train_done" if ok else "train_failed",
            {
                "job_id": job.id,
                "product_id": job.product_id,
                "product": p.name if p else None,
                "kind": job.kind,
                **extra,
            },
            durable=True,
        )

    async def train(self, job: TrainingJob, t0: float) -> None:
        jid = job.id
        p = {
            "model_size": "n",
            "epochs": 60,
            "imgsz": 640,
            "batch": 16,
            "negative_ratio": 1.0,
            "patience": 20,
            **(job.params or {}),
        }
        if job.kind == "draft":
            p["epochs"] = min(int(p["epochs"]), 15)
        work = self.s.data_subdir("datasets") / "jobs" / str(jid)
        resume_from = p.get("resume_from")
        if resume_from and Path(resume_from).exists():
            data_yaml, stats = work / "data.yaml", None
        else:

            def _build():
                with Session(self.sync_engine) as s:
                    return build_dataset(
                        s, job.product_id, work, camera_id=job.camera_id, negative_ratio=float(p["negative_ratio"])
                    )

            data_yaml, stats = await asyncio.to_thread(_build)
        if stats:
            await self.set_job(jid, stats={"dataset": stats.__dict__, "dataset_seconds": time.time() - t0})
        await self.check_cancel(jid)
        await self.set_job(jid, stage="train", epochs=int(p["epochs"]))
        project = self.s.data_subdir("models") / "runs" / str(jid)
        best: str | None = None
        t_train = time.time()

        async def on_line(text: str) -> None:
            nonlocal best
            if text.startswith("FCV_EPOCH "):
                r = json.loads(text[10:])
                async with get_sessionmaker()() as s:
                    s.add(
                        TrainingMetric(
                            job_id=jid,
                            epoch=r["epoch"],
                            box_loss=r["box_loss"],
                            cls_loss=r["cls_loss"],
                            dfl_loss=r["dfl_loss"],
                            precision=r["precision"],
                            recall=r["recall"],
                            map50=r["map50"],
                            map5095=r["map5095"],
                        )
                    )
                    await s.commit()
                await self.set_job(
                    jid, epoch=min(r["epoch"], r["epochs"]), epochs=r["epochs"], eta_sec=max(0.0, r["eta"] or 0.0)
                )
            elif text.startswith("FCV_DONE "):
                best = json.loads(text[9:])["best"]
            elif text.startswith("FCV_ERROR "):
                raise RuntimeError(json.loads(text[10:])["error"])

        args = [
            "training.run_train",
            "--data",
            str(data_yaml),
            "--out",
            str(project),
            "--model",
            str(p["model_size"]),
            "--epochs",
            str(p["epochs"]),
            "--imgsz",
            str(p["imgsz"]),
            "--batch",
            str(p["batch"]),
            "--patience",
            str(p["patience"]),
        ]
        if resume_from:
            args += ["--resume", str(resume_from)]
        rc = await self.run_sub(jid, args, on_line)
        if rc != 0 or not best or not Path(best).exists():
            raise RuntimeError(f"Train muvaffaqiyatsiz tugadi (kod {rc}). Loglarni ko'ring.")
        train_sec = time.time() - t_train

        # versiya
        async with get_sessionmaker()() as s:
            ver = (
                await s.execute(
                    select(func.coalesce(func.max(ModelVersion.version), 0)).where(
                        ModelVersion.product_id == job.product_id
                    )
                )
            ).scalar_one() + 1
            last_metric = (
                await s.execute(
                    select(TrainingMetric)
                    .where(TrainingMetric.job_id == jid)
                    .order_by(TrainingMetric.epoch.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
        mdir = self.s.data_subdir("models") / str(job.product_id) / f"v{ver}"
        mdir.mkdir(parents=True, exist_ok=True)
        pt_dst = mdir / "best.pt"
        os.replace(best, pt_dst)
        metrics = {
            "map50": last_metric.map50 if last_metric else None,
            "map5095": last_metric.map5095 if last_metric else None,
            "precision": last_metric.precision if last_metric else None,
            "recall": last_metric.recall if last_metric else None,
            "train_seconds": train_sec,
            "epochs": p["epochs"],
        }
        async with get_sessionmaker()() as s:
            mv = ModelVersion(
                product_id=job.product_id,
                camera_id=job.camera_id,
                version=ver,
                model_size=p["model_size"],
                is_draft=job.kind == "draft",
                metrics=metrics,
                pt_path=str(pt_dst.relative_to(self.s.data_path)),
                status="ready" if job.kind == "draft" else "building",
                job_id=jid,
            )
            s.add(mv)
            await s.commit()
            mv_id = mv.id
        await self.set_job(jid, model_version_id=mv_id, stage="validate")

        if job.kind == "full":
            await self.set_job(jid, stage="export")
            edir = self.s.data_subdir("engines") / str(job.product_id) / f"v{ver}"
            exp: dict = {}

            async def on_exp(text: str) -> None:
                nonlocal exp
                if text.startswith("FCV_EXPORT "):
                    exp = json.loads(text[11:])
                elif text.startswith("FCV_ERROR "):
                    raise RuntimeError(json.loads(text[10:])["error"])

            t_exp = time.time()
            rc = await self.run_sub(
                jid,
                [
                    "training.run_export",
                    "--pt",
                    str(pt_dst),
                    "--engine-out",
                    str(edir / "model.engine"),
                    "--data",
                    str(data_yaml),
                    "--imgsz",
                    str(p["imgsz"]),
                ],
                on_exp,
            )
            if rc != 0 or not exp.get("engine"):
                async with get_sessionmaker()() as s:
                    await s.execute(update(ModelVersion).where(ModelVersion.id == mv_id).values(status="failed"))
                    await s.commit()
                raise RuntimeError("TensorRT eksport muvaffaqiyatsiz. Loglarni ko'ring.")
            warn = None
            if (
                exp.get("pt_map50") is not None
                and exp.get("engine_map50") is not None
                and exp["pt_map50"] - exp["engine_map50"] > 0.03
            ):
                warn = f"Engine aniqligi .pt dan past: {exp['engine_map50']:.3f} < {exp['pt_map50']:.3f}"
            metrics.update(
                {
                    "export_seconds": time.time() - t_exp,
                    "engine_map50": exp.get("engine_map50"),
                    "pt_map50": exp.get("pt_map50"),
                    "export_warning": warn,
                }
            )
            async with get_sessionmaker()() as s:
                await s.execute(
                    update(ModelVersion)
                    .where(ModelVersion.id == mv_id)
                    .values(
                        engine_path=str(Path(exp["engine"]).relative_to(self.s.data_path)),
                        trt_version=exp.get("trt"),
                        driver_version=exp.get("driver"),
                        status="ready",
                        metrics=metrics,
                    )
                )
                await s.commit()
        total = time.time() - t0
        await self.set_job(
            jid,
            status="done",
            stage="done",
            finished_at=now(),
            eta_sec=0,
            stats={
                **((stats.__dict__ and {"dataset": stats.__dict__}) if stats else {}),
                "train_seconds": train_sec,
                "export_seconds": metrics.get("export_seconds"),
                "total_seconds": total,
            },
        )
        await self._emit_done(job, ok=True, version=ver, map50=metrics.get("map50"))

    async def autolabel(self, job: TrainingJob) -> None:
        p = job.params or {}
        conf = float(p.get("conf", 0.4))
        async with get_sessionmaker()() as s:
            mv = (
                await s.execute(
                    select(ModelVersion)
                    .where(ModelVersion.product_id == job.product_id, ModelVersion.status == "ready")
                    .order_by(ModelVersion.is_active.desc(), ModelVersion.version.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if mv is None:
                raise RuntimeError("Bu mahsulot uchun model yo'q — avval tez qoralama train qiling")
            q = select(DatasetImage).where(DatasetImage.status == "unlabeled", DatasetImage.is_empty.is_(False))
            if p.get("image_ids"):
                q = select(DatasetImage).where(DatasetImage.id.in_(p["image_ids"]))
            if p.get("camera_id"):
                q = q.where(DatasetImage.camera_id == p["camera_id"])
            imgs = (await s.execute(q.limit(int(p.get("limit", 2000))))).scalars().all()
        with Session(self.sync_engine) as ss:
            rois = crop_boxes(ss)
        items = []
        for im in imgs:
            items.append(
                {
                    "id": im.id,
                    "path": str(self.s.data_path / im.file_path),
                    "crop": [0, 0, im.width, im.height]
                    if im.crop
                    else list(roi_crop_box(rois.get(im.camera_id or -1), im.width, im.height)),
                }
            )
        if not items:
            await self.set_job(job.id, stats={"labeled": 0, "images": 0})
            return
        await self.set_job(job.id, stage="train", epochs=len(items), epoch=0)
        model = str(self.s.data_path / mv.pt_path)
        done = 0
        labeled = 0

        async def on_line(text: str) -> None:
            nonlocal done, labeled
            if not text.startswith("FCV_PRED "):
                return
            r = json.loads(text[9:])
            done += 1
            if r["boxes"]:
                labeled += 1
                async with get_sessionmaker()() as s:
                    img = await s.get(DatasetImage, r["id"])
                    if img is not None and img.status == "unlabeled":
                        for b in r["boxes"]:
                            s.add(
                                Annotation(
                                    image_id=img.id,
                                    product_id=job.product_id,
                                    bbox=[round(v, 5) for v in b["bbox"]],
                                    status="auto",
                                    confidence=b["conf"],
                                )
                            )
                        img.status = "auto"
                        await s.commit()
            if done % 10 == 0:
                await self.set_job(job.id, epoch=done)

        rc = await self.run_sub(
            job.id,
            ["training.run_autolabel"],
            on_line,
            stdin=json.dumps({"model": model, "conf": conf, "images": items}).encode(),
        )
        if rc != 0:
            raise RuntimeError(f"Avto-belgilash xato bilan tugadi (kod {rc})")
        await self.set_job(job.id, epoch=done, stats={"labeled": labeled, "images": len(items)})
