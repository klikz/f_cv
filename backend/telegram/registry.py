"""Xabar turlari registri (6.4) — yangi tur qo'shish uchun shu ro'yxatga yozuv qo'shiladi.

Har tur: kod, nomi, vazifa (counting | equipment | system), parametrlari, hodisadan matn yasash funksiyasi.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def _t(ts: float) -> str:
    return datetime.fromtimestamp(ts, ZoneInfo(get_settings().timezone)).strftime("%H:%M:%S")


def _dur(sec: float) -> str:
    sec = int(sec)
    h, m = divmod(sec // 60, 60)
    return f"{h} soat {m} daq" if h else (f"{m} daq" if m else f"{sec} s")


@dataclass
class MessageType:
    code: str
    title: str
    task: str  # counting | equipment | system | report
    events: tuple[str, ...]
    render: Callable[[dict, dict], str]
    params: dict[str, Any] = field(default_factory=dict)  # standart parametrlar
    per_camera: bool = True
    with_image: bool = False
    param_labels: dict[str, str] = field(default_factory=dict)  # UI uchun: {"minutes": "har N daqiqada"}


def r_count(e: dict, ctx: dict) -> str:
    status = " ⚠️ <b>noaniq</b>" if e.get("status") == "uncertain" else ""
    rev = " (teskari)" if e.get("direction") == "reverse" else ""
    return (
        f"📦 <b>{e.get('product') or 'Noaniq'}</b>{status}{rev}\n"
        f"Kamera: {ctx.get('camera', '—')}\nVaqt: {_t(e['ts'])}\n"
        f"Smena bo'yicha: <b>{e.get('shift_total', 0)}</b> ta (kamera jami {e.get('camera_total', 0)})"
    )


def r_eq_stopped(e: dict, ctx: dict) -> str:
    mins = ctx.get("params", {}).get("minutes", 5)
    return f"🛑 <b>Uskuna to'xtadi</b> ({mins} daqiqadan ortiq)\nKamera: {ctx.get('camera', '—')}\nTo'xtagan vaqt: {_t(e['since'])}"


def r_eq_started(e: dict, ctx: dict) -> str:
    d = f"\nTo'xtash davomiyligi: {_dur(e['stopped_sec'])}" if e.get("stopped_sec") else ""
    return f"✅ <b>Uskuna qayta ishga tushdi</b>\nKamera: {ctx.get('camera', '—')}\nVaqt: {_t(e['ts'])}{d}"


def r_cam_off(e: dict, ctx: dict) -> str:
    err = f"\nSabab: {e['error']}" if e.get("error") else ""
    return f"📵 <b>Kamera uzildi</b>: {ctx.get('camera', '—')}\nVaqt: {_t(e['ts'])}{err}"


def r_cam_on(e: dict, ctx: dict) -> str:
    return f"📶 <b>Kamera tiklandi</b>: {ctx.get('camera', '—')}\nVaqt: {_t(e['ts'])}"


def r_train_done(e: dict, ctx: dict) -> str:
    m = f"\nmAP50: {e['map50']:.3f}" if isinstance(e.get("map50"), (int, float)) else ""
    return f'🎓 <b>Train tugadi</b>: {e.get("product", "—")} (v{e.get("version", "?")}){m}\nYangi versiyani "Modellar" sahifasida faollashtiring.'


def r_train_failed(e: dict, ctx: dict) -> str:
    return f"❌ <b>Train xato bilan tugadi</b>: {e.get('product', '—')}\n{(e.get('error') or '')[:300]}"


def r_shift_report(e: dict, ctx: dict) -> str:
    """e: {shift, shift_date, start, end, final, interval_min, summary} (start/end — unix ts)."""
    sm = e["summary"]
    head = "🏁 <b>Smena yakuni</b>" if e.get("final") else "📊 <b>Smena hisoboti</b>"
    till = _t(e["end"])[:5] + ("" if e.get("final") else " (hozir)")
    lines = [
        f"{head} — {e.get('shift', '—')} ({e.get('shift_date', '')})",
        f"Kamera: {ctx.get('camera', '—')}",
        f"Vaqt: {_t(e['start'])[:5]} – {till}",
    ]
    c = sm.get("counting")
    if c is not None:
        rec = f" (oxirgi {e['interval_min']} daq: {c['recent']})" if c.get("recent") is not None else ""
        lines += ["", f"📦 Sanaldi: <b>{c['total']}</b> ta{rec}"]
        lines += [f"  • {p['name']} — {p['count']}" for p in c["by_product"][:10]]
        if len(c["by_product"]) > 10:
            lines.append(f"  • boshqalar — {sum(p['count'] for p in c['by_product'][10:])}")
        if c["uncertain"]:
            lines.append(f"  ⚠️ Noaniq: {c['uncertain']}")
    q = sm.get("equipment")
    if q is not None:
        util = f" ({q['utilization_pct']}%)" if q["utilization_pct"] is not None else ""
        lines += [
            "",
            f"⚙️ Ishladi: <b>{_dur(q['running'])}</b>{util}",
            f"  To'xtadi: {_dur(q['stopped'])} ({q['stops']} marta)",
        ]
        if q["unknown"] >= 60:
            lines.append(f"  Noma'lum: {_dur(q['unknown'])}")
        if q["cycles"]:
            avg = f", o'rtacha {q['avg_cycle_sec']} s" if q["avg_cycle_sec"] is not None else ""
            lines.append(f"  Sikllar: {q['cycles']}{avg}; mikro-to'xtash: {q['micro_stops']}")
    if c is None and q is None:
        lines += ["", "Bu kamerada sanoq yoki uskuna vazifasi yoqilmagan."]
    if sm.get("gap_sec", 0) >= 60:
        lines += ["", f"📵 Sanalmagan vaqt: {_dur(sm['gap_sec'])}"]
    return "\n".join(lines)


def r_test(e: dict, ctx: dict) -> str:
    return "🔔 F_CV: sinov xabari. Bot ishlayapti."


REGISTRY: dict[str, MessageType] = {
    t.code: t
    for t in [
        MessageType("count", "Mahsulot sanaldi", "counting", ("count",), r_count, with_image=True),
        MessageType(
            "equipment_stopped",
            "Uskuna to'xtadi (> N daq)",
            "equipment",
            ("equipment_state",),
            r_eq_stopped,
            {"minutes": 5},
        ),
        MessageType("equipment_started", "Uskuna qayta ishga tushdi", "equipment", ("equipment_state",), r_eq_started),
        MessageType(
            "shift_report",
            "Smena hisoboti",
            "report",
            (),  # hodisadan emas — telegram-service jadval bo'yicha yuboradi
            r_shift_report,
            {"minutes": 60, "delay": 30},
            param_labels={
                "minutes": "daqiqada bir (smena davomida)",
                "delay": "daqiqa — smena tugagach yakuniy hisobot",
            },
        ),
        MessageType("camera_offline", "Kamera uzildi", "system", ("camera_offline",), r_cam_off),
        MessageType("camera_online", "Kamera tiklandi", "system", ("camera_online",), r_cam_on),
        MessageType("train_done", "Train tugadi", "system", ("train_done",), r_train_done, per_camera=False),
        MessageType("train_failed", "Train xato", "system", ("train_failed",), r_train_failed, per_camera=False),
    ]
}

TEST = MessageType("test", "Sinov", "system", (), r_test, per_camera=False)


def types_for_event(kind: str, event: dict) -> list[MessageType]:
    out = [t for t in REGISTRY.values() if kind in t.events]
    if kind == "equipment_state":
        st = event.get("state")
        out = [
            t
            for t in out
            if (t.code == "equipment_stopped" and st == "stopped")
            or (t.code == "equipment_started" and st == "running")
        ]
    return out


def describe() -> list[dict]:
    return [
        {
            "code": t.code,
            "title": t.title,
            "task": t.task,
            "params": t.params,
            "param_labels": t.param_labels,
            "per_camera": t.per_camera,
        }
        for t in REGISTRY.values()
    ]
