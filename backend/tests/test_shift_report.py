"""Telegram "Smena hisoboti": jadval (oraliq + yakuniy), ko'rsatkichlar va matn."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.models.cameras import Camera
from app.models.catalog import Product
from app.models.counting import CountEvent
from app.models.equipment import EquipmentInterval
from app.models.shifts import Shift
from app.models.tasks import CameraTask
from app.models.telegram import NotificationOutbox, TelegramChat, TelegramSubscription
from app.services.shifts import ShiftDef, shift_bounds

TZ = ZoneInfo("Asia/Tashkent")
EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


def local(d, hh, mm, ss=0):
    return datetime(2026, 11, d, hh, mm, ss, tzinfo=TZ)


def test_shift_bounds_overnight():
    night = ShiftDef(2, "Tungi", time(19, 0), time(8, 0), EPOCH)
    a, b = shift_bounds(night, date(2026, 11, 26), TZ)
    assert a == local(26, 19, 0) and b == local(27, 8, 0)


async def _setup(db):
    # testlar smenalarni o'zgartirmaydi; standart to'plam bo'lmasa — qo'shamiz
    if not (await db.execute(select(Shift))).first():
        db.add_all(
            [
                Shift(name="Kunduzgi smena", start_time=time(8), end_time=time(19), effective_from=EPOCH),
                Shift(name="Tungi smena", start_time=time(19), end_time=time(8), effective_from=EPOCH, position=1),
            ]
        )
    cam = Camera(name="Liniya 1", main_rtsp_url="rtsp://x")
    prod = Product(code="A1", name="Model A")
    chat = TelegramChat(chat_id=111, title="Sex", type="group", active=True)
    db.add_all([cam, prod, chat])
    await db.flush()
    db.add_all(
        [
            CameraTask(camera_id=cam.id, task_type="counting", enabled=True),
            CameraTask(camera_id=cam.id, task_type="equipment", enabled=True),
            TelegramSubscription(
                chat_id=chat.id,
                camera_id=cam.id,
                task_type="report",
                message_type="shift_report",
                params={"minutes": 60},
            ),
        ]
    )
    day = (await db.execute(select(Shift).where(Shift.start_time == time(8)))).scalars().first()
    for m in (10, 20, 70):  # 08:10, 08:20, 09:10
        db.add(
            CountEvent(
                camera_id=cam.id,
                product_id=prod.id,
                status="confirmed",
                ts=local(27, 8, 0) + timedelta(minutes=m),
                shift_id=day.id,
                shift_date=date(2026, 11, 27),
            )
        )
    db.add(EquipmentInterval(camera_id=cam.id, state="running", start_ts=local(27, 8, 0), end_ts=local(27, 9, 0)))
    db.add(EquipmentInterval(camera_id=cam.id, state="stopped", start_ts=local(27, 9, 0), end_ts=None))
    await db.commit()


async def test_shift_report_schedule(db, redis, monkeypatch):
    import telegram.service as svc

    await _setup(db)
    clock = {"t": local(27, 9, 5)}
    monkeypatch.setattr(svc, "now", lambda: clock["t"].astimezone(UTC))
    s = svc.TelegramService(redis)

    async def outbox():
        db.expire_all()
        return (await db.execute(select(NotificationOutbox).order_by(NotificationOutbox.id))).scalars().all()

    await s.shift_report_tick()  # obuna smena o'rtasida boshlandi — darhol yubormaydi
    assert await outbox() == []

    clock["t"] = local(27, 9, 30)
    await s.shift_report_tick()
    assert await outbox() == []

    clock["t"] = local(27, 10, 0, 20)  # 2-slot
    await s.shift_report_tick()
    rows = await outbox()
    assert len(rows) == 1 and rows[0].message_type == "shift_report"
    txt = rows[0].text
    assert "Smena hisoboti" in txt and "Liniya 1" in txt
    assert "Sanaldi: <b>3</b>" in txt and "oxirgi 60 daq: 1" in txt and "Model A — 3" in txt
    assert "Ishladi: <b>1 soat 0 daq</b>" in txt and "(1 marta)" in txt

    await s.shift_report_tick()  # shu slotda takror yo'q
    assert len(await outbox()) == 1

    clock["t"] = local(27, 19, 0, 30)  # smena tugadi → yakuniy
    await s.shift_report_tick()
    rows = await outbox()
    assert len(rows) == 2
    assert "Smena yakuni" in rows[1].text and "08:00 – 19:00" in rows[1].text

    clock["t"] = local(27, 19, 1)
    await s.shift_report_tick()
    assert len(await outbox()) == 2
