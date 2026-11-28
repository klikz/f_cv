"""Telegram "Smena hisoboti": faqat smena tugagach yakuniy, ko'rsatkichlar va matn."""

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
                params={},
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

    # smena davomida (soatlab ham) hech narsa yuborilmaydi
    for h, m in ((9, 5), (10, 0), (11, 0), (15, 0), (18, 59)):
        clock["t"] = local(27, h, m, 20)
        await s.shift_report_tick()
    assert await outbox() == []

    clock["t"] = local(27, 19, 0, 30)  # smena tugadi — yakuniy hali emas (30 daq kechikish)
    await s.shift_report_tick()
    assert await outbox() == []

    clock["t"] = local(27, 19, 30, 10)  # tugaganiga 30 daq → yakuniy
    await s.shift_report_tick()
    rows = await outbox()
    assert len(rows) == 1 and rows[0].message_type == "shift_report"
    txt = rows[0].text
    assert "Smena yakuni" in txt and "08:00 – 19:00" in txt and "Liniya 1" in txt
    assert "Sanaldi: <b>3</b>" in txt and "Model A — 3" in txt and "oxirgi" not in txt
    assert "Ishladi: <b>1 soat 0 daq</b>" in txt and "(1 marta)" in txt

    for h, m in ((19, 31), (20, 30), (23, 0)):  # tungi smena davomida — takror ham, oraliq ham yo'q
        clock["t"] = local(27, h, m)
        await s.shift_report_tick()
    assert len(await outbox()) == 1


async def test_shift_report_final_after_downtime(db, redis, monkeypatch):
    """Servis smena almashuvi paytida ishlamagan bo'lsa ham, qaytgach yakuniy hisobot yuboriladi."""
    import telegram.service as svc

    await _setup(db)
    sub = (await db.execute(select(TelegramSubscription))).scalars().one()
    sub.params = {"delay": 10}
    await db.commit()
    clock = {"t": local(27, 18, 0)}
    monkeypatch.setattr(svc, "now", lambda: clock["t"].astimezone(UTC))
    await svc.TelegramService(redis).shift_report_tick()

    clock["t"] = local(27, 21, 0)  # yangi jarayon, oradagi tiklar yo'q
    await svc.TelegramService(redis).shift_report_tick()
    db.expire_all()
    rows = (await db.execute(select(NotificationOutbox))).scalars().all()
    assert len(rows) == 1 and "Smena yakuni" in rows[0].text


async def test_shift_report_now(db, redis, monkeypatch):
    import telegram.service as svc

    await _setup(db)
    chat_id = (await db.execute(select(TelegramChat.id))).scalar_one()
    cam_id = (await db.execute(select(Camera.id))).scalar_one()
    monkeypatch.setattr(svc, "now", lambda: local(27, 10, 0).astimezone(UTC))
    mid = await svc.TelegramService(redis).send_shift_report_now(chat_id, cam_id)
    db.expire_all()
    m = await db.get(NotificationOutbox, mid)
    assert "Smena hisoboti" in m.text and "(hozir)" in m.text and "Sanaldi: <b>3</b>" in m.text

    monkeypatch.setattr(svc, "now", lambda: local(27, 19, 5).astimezone(UTC))  # tungi smena boshida
    mid = await svc.TelegramService(redis).send_shift_report_now(chat_id, cam_id)
    db.expire_all()
    assert "Tungi smena" in (await db.get(NotificationOutbox, mid)).text


def test_last_ended_shift():
    from app.services.shifts import last_ended_shift

    day = ShiftDef(1, "Kunduzgi", time(8, 0), time(19, 0), EPOCH)
    night = ShiftDef(2, "Tungi", time(19, 0), time(8, 0), EPOCH)
    s, d, _, b = last_ended_shift([day, night], local(27, 19, 0), TZ)
    assert s.id == 1 and d == date(2026, 11, 27) and b == local(27, 19, 0)
    s, d, _, b = last_ended_shift([day, night], local(27, 7, 0), TZ)  # tungi smena hali davom etmoqda
    assert s.id == 1 and d == date(2026, 11, 26) and b == local(26, 19, 0)
    s, d, _, b = last_ended_shift([day, night], local(27, 8, 0), TZ)
    assert s.id == 2 and d == date(2026, 11, 26) and b == local(27, 8, 0)
