"""Hisobotlar (asos): sanoqlar, uskuna ish/to'xtash vaqti va sikllar, sanalmagan oraliqlar, Excel eksport."""

import io
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.models.cameras import Camera, CoverageGap
from app.models.catalog import Product
from app.models.counting import CountEvent
from app.models.equipment import CycleEvent, EquipmentInterval
from app.models.shifts import Shift
from app.models.tasks import CountingConfig
from app.services.shift_summary import count_sign

router = APIRouter(prefix="/reports", tags=["reports"])


def _tz():
    return ZoneInfo(get_settings().timezone)


def _range(d_from: date, d_to: date) -> tuple[datetime, datetime]:
    tz = _tz()
    return datetime.combine(d_from, datetime.min.time(), tz), datetime.combine(
        d_to + timedelta(days=1), datetime.min.time(), tz
    )


async def _names(session):
    return (
        dict((await session.execute(select(Camera.id, Camera.name))).all()),
        dict((await session.execute(select(Product.id, Product.name))).all()),
        dict((await session.execute(select(Shift.id, Shift.name))).all()),
    )


@router.get("/counts")
async def counts_report(
    session: SessionDep,
    d_from: date = Query(alias="from"),
    d_to: date = Query(alias="to"),
    shift_id: int | None = None,
    camera_id: int | None = None,
    product_id: int | None = None,
) -> dict:
    """Smena sanasi bo'yicha (yarim tundan o'tuvchi smena boshlangan sanaga). Bekor qilinganlar hisobga olinmaydi,
    tuzatilganlar — tuzatilgan mahsulot bilan; teskari yo'nalish kamera siyosatiga ko'ra ayiriladi."""
    q = select(CountEvent).where(
        CountEvent.shift_date >= d_from, CountEvent.shift_date <= d_to, CountEvent.status != "cancelled"
    )
    if shift_id:
        q = q.where(CountEvent.shift_id == shift_id)
    if camera_id:
        q = q.where(CountEvent.camera_id == camera_id)
    if product_id:
        q = q.where(CountEvent.product_id == product_id)
    rows = (await session.execute(q.order_by(CountEvent.ts))).scalars().all()
    cfgs = {c.camera_id: c for c in (await session.execute(select(CountingConfig))).scalars()}
    cams, prods, shifts = await _names(session)
    tz = _tz()
    by_day: dict[str, int] = defaultdict(int)
    by_shift: dict[tuple, int] = defaultdict(int)
    by_hour: dict[str, int] = defaultdict(int)
    by_prod: dict[int | None, dict] = {}
    by_cam: dict[int | None, int] = defaultdict(int)
    total = uncertain = corrected = 0
    for e in rows:
        sign = count_sign(e.direction, cfgs.get(e.camera_id or 0))
        if not sign:
            continue  # "alohida" — asosiy hisobga kirmaydi
        total += sign
        uncertain += int(e.status == "uncertain")
        corrected += int(e.status == "corrected")
        d = e.shift_date.isoformat() if e.shift_date else e.ts.astimezone(tz).date().isoformat()
        by_day[d] += sign
        by_shift[(d, e.shift_id)] += sign
        by_hour[e.ts.astimezone(tz).strftime("%Y-%m-%d %H:00")] += sign
        p = by_prod.setdefault(
            e.product_id,
            {"product_id": e.product_id, "name": prods.get(e.product_id or 0, "Noaniq"), "count": 0, "uncertain": 0},
        )
        p["count"] += sign
        p["uncertain"] += int(e.status == "uncertain")
        by_cam[e.camera_id] += sign
    cancelled = (
        await session.execute(
            select(func.count()).where(
                CountEvent.shift_date >= d_from, CountEvent.shift_date <= d_to, CountEvent.status == "cancelled"
            )
        )
    ).scalar_one()
    return {
        "total": total,
        "uncertain": uncertain,
        "corrected": corrected,
        "cancelled": cancelled,
        "by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
        "by_shift": [
            {"date": d, "shift_id": s, "shift": shifts.get(s or 0, "Smenadan tashqari"), "count": v}
            for (d, s), v in sorted(by_shift.items(), key=lambda x: (x[0][0], x[0][1] or 0))
        ],
        "by_hour": [{"hour": k, "count": v} for k, v in sorted(by_hour.items())],
        "by_product": sorted(by_prod.values(), key=lambda x: -x["count"]),
        "by_camera": [{"camera_id": k, "camera": cams.get(k or 0), "count": v} for k, v in by_cam.items()],
    }


@router.get("/equipment")
async def equipment_report(
    session: SessionDep,
    d_from: date = Query(alias="from"),
    d_to: date = Query(alias="to"),
    shift_id: int | None = None,
    camera_id: int | None = None,
) -> dict:
    a, b = _range(d_from, d_to)
    now = datetime.now(UTC)
    q = select(EquipmentInterval).where(
        EquipmentInterval.start_ts < b, (EquipmentInterval.end_ts.is_(None)) | (EquipmentInterval.end_ts > a)
    )
    if camera_id:
        q = q.where(EquipmentInterval.camera_id == camera_id)
    if shift_id:
        q = q.where(EquipmentInterval.shift_id == shift_id)
    ivs = (await session.execute(q.order_by(EquipmentInterval.start_ts))).scalars().all()
    cq = select(CycleEvent).where(CycleEvent.end_ts >= a, CycleEvent.end_ts < b)
    if camera_id:
        cq = cq.where(CycleEvent.camera_id == camera_id)
    if shift_id:
        cq = cq.where(CycleEvent.shift_id == shift_id)
    cycles = (await session.execute(cq)).scalars().all()
    cams, _, _ = await _names(session)
    per: dict[int, dict] = {}
    for iv in ivs:
        s = max(iv.start_ts, a)
        e = min(iv.end_ts or now, b, now)
        d = max(0.0, (e - s).total_seconds())
        c = per.setdefault(
            iv.camera_id,
            {
                "camera_id": iv.camera_id,
                "camera": cams.get(iv.camera_id),
                "running": 0.0,
                "stopped": 0.0,
                "unknown": 0.0,
                "timeline": [],
                "cycles": 0,
                "durations": [],
                "micro_stops": 0,
            },
        )
        c[iv.state if iv.state in ("running", "stopped") else "unknown"] += d
        c["timeline"].append({"state": iv.state, "start": s.isoformat(), "end": e.isoformat()})
    for cy in cycles:
        c = per.setdefault(
            cy.camera_id,
            {
                "camera_id": cy.camera_id,
                "camera": cams.get(cy.camera_id),
                "running": 0.0,
                "stopped": 0.0,
                "unknown": 0.0,
                "timeline": [],
                "cycles": 0,
                "durations": [],
                "micro_stops": 0,
            },
        )
        c["cycles"] += 1
        c["durations"].append(round(cy.duration, 2))
        c["micro_stops"] += int(cy.is_micro_stop)
    out = []
    for c in per.values():
        known = c["running"] + c["stopped"]
        ds = sorted(c["durations"])
        c["utilization_pct"] = round(c["running"] / known * 100, 1) if known else None
        c["avg_cycle_sec"] = round(sum(ds) / len(ds), 2) if ds else None
        c["median_cycle_sec"] = ds[len(ds) // 2] if ds else None
        c["durations"] = ds[-2000:]
        out.append(c)
    return {"cameras": sorted(out, key=lambda x: x["camera_id"])}


@router.get("/gaps")
async def gaps_report(
    session: SessionDep,
    d_from: date = Query(alias="from"),
    d_to: date = Query(alias="to"),
    camera_id: int | None = None,
) -> list[dict]:
    a, b = _range(d_from, d_to)
    q = select(CoverageGap).where(CoverageGap.start_ts < b, (CoverageGap.end_ts.is_(None)) | (CoverageGap.end_ts > a))
    if camera_id:
        q = q.where((CoverageGap.camera_id == camera_id) | CoverageGap.camera_id.is_(None))
    cams, _, _ = await _names(session)
    now = datetime.now(UTC)
    labels = {"camera": "Kamera uzilgan", "train": "Train ketgan", "service": "Servis o'chgan"}
    return [
        {
            "camera_id": g.camera_id,
            "camera": cams.get(g.camera_id or 0, "Barcha kameralar"),
            "reason": g.reason,
            "reason_label": labels.get(g.reason, g.reason),
            "task_type": g.task_type,
            "start": max(g.start_ts, a).isoformat(),
            "end": min(g.end_ts or now, b).isoformat(),
            "open": g.end_ts is None,
            "seconds": round((min(g.end_ts or now, b) - max(g.start_ts, a)).total_seconds()),
            "detail": g.detail,
        }
        for g in (await session.execute(q.order_by(CoverageGap.start_ts))).scalars()
    ]


@router.get("/export.xlsx")
async def export_xlsx(
    session: SessionDep,
    d_from: date = Query(alias="from"),
    d_to: date = Query(alias="to"),
    shift_id: int | None = None,
    camera_id: int | None = None,
) -> StreamingResponse:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    c = await counts_report(session, d_from, d_to, shift_id, camera_id, None)
    e = await equipment_report(session, d_from, d_to, shift_id, camera_id)
    g = await gaps_report(session, d_from, d_to, camera_id)
    wb = Workbook()
    bold = Font(bold=True)

    def sheet(title, headers, rows, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append(headers)
        for cell in ws[1]:
            cell.font = bold
        for r in rows:
            ws.append(r)
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(
                12, min(40, max(len(str(x.value or "")) for x in col) + 2)
            )

    sheet(
        "Sanoq — mahsulotlar",
        ["Mahsulot", "Soni", "Shundan noaniq"],
        [[p["name"], p["count"], p["uncertain"]] for p in c["by_product"]],
        first=True,
    )
    sheet(
        "Sanoq — smenalar",
        ["Smena sanasi", "Smena", "Soni"],
        [[r["date"], r["shift"], r["count"]] for r in c["by_shift"]],
    )
    sheet("Sanoq — soatlar", ["Soat", "Soni"], [[r["hour"], r["count"]] for r in c["by_hour"]])
    sheet(
        "Uskuna",
        [
            "Kamera",
            "Ishladi (daq)",
            "To'xtadi (daq)",
            "Noma'lum (daq)",
            "Ish vaqti %",
            "Sikllar",
            "O'rtacha sikl (s)",
            "Mikro-to'xtash",
        ],
        [
            [
                x["camera"],
                round(x["running"] / 60, 1),
                round(x["stopped"] / 60, 1),
                round(x["unknown"] / 60, 1),
                x["utilization_pct"],
                x["cycles"],
                x["avg_cycle_sec"],
                x["micro_stops"],
            ]
            for x in e["cameras"]
        ],
    )
    sheet(
        "Sanalmagan oraliqlar",
        ["Kamera", "Sabab", "Boshlanish", "Tugash", "Davomiylik (daq)"],
        [[x["camera"], x["reason_label"], x["start"], x["end"], round(x["seconds"] / 60, 1)] for x in g],
    )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"hisobot_{d_from}_{d_to}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
