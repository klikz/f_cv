"""telegram-service: long polling (aiogram 3), chatlarni avto aniqlash, hodisalar → outbox → yuborish.

Tizimning qolgan qismi Telegramga bog'liq emas: hodisalar Redis Stream'da (`fcv:stream:events`) saqlanadi,
outbox PostgreSQL'da — internet yo'q bo'lsa xabarlar navbatda kutadi va qaytganda ketadi.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select, update

from app.core import keys
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models.cameras import Camera
from app.models.counting import CountEvent
from app.models.telegram import NotificationOutbox, TelegramChat, TelegramSubscription
from app.services.settings_store import get_setting
from app.services.shift_summary import camera_shift_summary
from app.services.shifts import ShiftResolver, shift_bounds
from telegram.registry import REGISTRY, types_for_event

log = logging.getLogger(__name__)
GROUP = "telegram"
SHIFT_REPORT_STATE = keys.P + "telegram:shift_report"  # hash: "{chat}:{camera}" -> json holat
FINAL_GRACE_SEC = 6 * 3600  # servis shuncha vaqt ichida qaytsa, o'tgan smena yakuniy hisoboti baribir yuboriladi
CONSUMER = "tg-1"


def now() -> datetime:
    return datetime.now(UTC)


class TelegramService:
    def __init__(self, redis: Redis) -> None:
        self.r = redis
        self.bot = None
        self.dp = None
        self.token: str | None = None
        self.state = "starting"
        self.username: str | None = None
        self.last_sent: dict[int, float] = {}
        self.pending_stops: dict[int, dict] = {}  # camera_id -> {since, notified}
        self.shifts = ShiftResolver()

    # ---------- holat ----------
    async def set_status(self, state: str, error: str | None = None) -> None:
        self.state = state
        await self.r.hset(
            keys.TELEGRAM_STATUS,
            mapping={"state": state, "error": error or "", "username": self.username or "", "ts": time.time()},
        )
        await self.r.expire(keys.TELEGRAM_STATUS, 60)

    async def resolve_token(self) -> str:
        async with get_sessionmaker()() as s:
            t = await get_setting(s, "telegram.token")
        return (t or get_settings().telegram_bot_token or "").strip()

    # ---------- chatlar ----------
    async def upsert_chat(self, chat_id: int, title: str, ctype: str, active: bool = True) -> None:
        async with get_sessionmaker()() as s:
            row = (await s.execute(select(TelegramChat).where(TelegramChat.chat_id == chat_id))).scalar_one_or_none()
            created = row is None
            if row is None:
                row = TelegramChat(chat_id=chat_id, title=title, type=ctype, active=active)
                s.add(row)
            else:
                row.title, row.type, row.active = title, ctype, active
            await s.commit()
        await self.r.publish(
            keys.CH_EVENTS,
            json.dumps(
                {
                    "kind": "telegram_chat",
                    "ts": time.time(),
                    "chat_id": chat_id,
                    "title": title,
                    "active": active,
                    "created": created,
                },
                ensure_ascii=False,
            ),
        )
        log.info("Chat %s: %s (%s) faol=%s", "qo'shildi" if created else "yangilandi", title, chat_id, active)

    async def migrate_chat(self, old_id: int, new_id: int) -> None:
        async with get_sessionmaker()() as s:
            await s.execute(
                update(TelegramChat).where(TelegramChat.chat_id == old_id).values(chat_id=new_id, type="supergroup")
            )
            await s.commit()

    def build_dispatcher(self):
        from aiogram import Dispatcher, F
        from aiogram.filters import Command
        from aiogram.types import ChatMemberUpdated, Message

        dp = Dispatcher()

        @dp.my_chat_member()
        async def on_member(ev: ChatMemberUpdated) -> None:
            st = ev.new_chat_member.status
            active = st in ("member", "administrator", "creator")
            title = ev.chat.title or ev.chat.full_name or str(ev.chat.id)
            await self.upsert_chat(ev.chat.id, title, ev.chat.type, active)
            if not active:
                await self.cancel_chat_messages(ev.chat.id, "Bot chatdan chiqarildi")

        @dp.message(Command("start"))
        async def on_start(m: Message) -> None:
            title = m.chat.title or m.chat.full_name or str(m.chat.id)
            await self.upsert_chat(m.chat.id, title, m.chat.type, True)
            await m.answer(
                "Assalomu alaykum! Bu chat F_CV tizimida ro'yxatga olindi. Xabarlar turini veb-interfeysdagi Telegram sahifasida tanlang."
            )

        @dp.message(F.new_chat_title)
        async def on_title(m: Message) -> None:
            await self.upsert_chat(m.chat.id, m.new_chat_title or str(m.chat.id), m.chat.type, True)

        @dp.message(F.migrate_to_chat_id)
        async def on_migrate(m: Message) -> None:
            await self.migrate_chat(m.chat.id, m.migrate_to_chat_id)

        return dp

    async def cancel_chat_messages(self, tg_chat_id: int, reason: str) -> None:
        async with get_sessionmaker()() as s:
            chat = (
                await s.execute(select(TelegramChat).where(TelegramChat.chat_id == tg_chat_id))
            ).scalar_one_or_none()
            if chat is None:
                return
            chat.active = False
            await s.execute(
                update(NotificationOutbox)
                .where(NotificationOutbox.chat_id == chat.id, NotificationOutbox.status == "pending")
                .values(status="cancelled", last_error=reason)
            )
            await s.commit()

    # ---------- polling ----------
    async def polling_loop(self, stop: asyncio.Event) -> None:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.exceptions import TelegramUnauthorizedError

        backoff = 2.0
        while not stop.is_set():
            token = await self.resolve_token()
            if not token:
                await self.set_status("no_token", "Bot tokeni kiritilmagan")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), 10)
                continue
            self.token = token
            self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
            try:
                me = await self.bot.get_me()
                self.username = me.username
                await self.set_status("connected")
                backoff = 2.0
                self.dp = self.build_dispatcher()
                polling = asyncio.create_task(
                    self.dp.start_polling(self.bot, handle_signals=False, allowed_updates=["message", "my_chat_member"])
                )
                token_watch = asyncio.create_task(self._watch_token(token, stop))
                done, _ = await asyncio.wait(
                    {polling, token_watch, asyncio.create_task(stop.wait())}, return_when=asyncio.FIRST_COMPLETED
                )
                with contextlib.suppress(Exception):
                    await self.dp.stop_polling()
                for t in (polling, token_watch):
                    t.cancel()
            except TelegramUnauthorizedError:
                await self.set_status("bad_token", "Bot tokeni noto'g'ri")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), 30)
            except Exception as e:
                await self.set_status("no_internet", f"Telegramga ulanib bo'lmadi: {e.__class__.__name__}")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), backoff)
                backoff = min(backoff * 2, 60)
            finally:
                with contextlib.suppress(Exception):
                    await self.bot.session.close()

    async def _watch_token(self, token: str, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await asyncio.sleep(5)
            await self.set_status(self.state)
            if await self.resolve_token() != token:
                log.info("Bot tokeni o'zgardi — qayta ulanish")
                return

    # ---------- hodisalar → outbox ----------
    async def ensure_group(self) -> None:
        with contextlib.suppress(Exception):
            await self.r.xgroup_create(keys.STREAM_EVENTS, GROUP, id="$", mkstream=True)

    async def events_loop(self, stop: asyncio.Event) -> None:
        await self.ensure_group()
        while not stop.is_set():
            try:
                res = await self.r.xreadgroup(GROUP, CONSUMER, {keys.STREAM_EVENTS: ">"}, count=50, block=2000)
                for _, msgs in res or []:
                    for mid, fields in msgs:
                        try:
                            await self.handle_event(json.loads(fields["data"]))
                        except Exception:
                            log.exception("hodisani qayta ishlab bo'lmadi")
                        await self.r.xack(keys.STREAM_EVENTS, GROUP, mid)
                await self.check_delayed_stops()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("hodisalar oqimi: %s", e)
                await asyncio.sleep(2)

    async def handle_event(self, ev: dict) -> None:
        kind = ev.get("kind", "")
        if kind == "equipment_state":
            cid = ev.get("camera_id")
            if ev.get("state") == "stopped":
                self.pending_stops[cid] = {"since": ev.get("since") or ev["ts"], "notified": set()}
                return  # "to'xtadi > N daq" — kechiktirilgan tekshiruvda
            if ev.get("state") == "running":
                p = self.pending_stops.pop(cid, None)
                if p:
                    ev = {**ev, "stopped_sec": ev["ts"] - p["since"]}
                    # faqat to'xtash haqida xabar yuborilgan chatlarga "qayta ishga tushdi"
                    await self.enqueue(ev, [REGISTRY["equipment_started"]], only_chats=p["notified"] or None)
                return
        types = types_for_event(kind, ev)
        if types:
            await self.enqueue(ev, types)

    async def check_delayed_stops(self) -> None:
        if not self.pending_stops:
            return
        nowt = time.time()
        async with get_sessionmaker()() as s:
            subs = (
                (
                    await s.execute(
                        select(TelegramSubscription).where(TelegramSubscription.message_type == "equipment_stopped")
                    )
                )
                .scalars()
                .all()
            )
        for cid, p in list(self.pending_stops.items()):
            for sub in subs:
                if sub.camera_id != cid or sub.chat_id in p["notified"]:
                    continue
                mins = float((sub.params or {}).get("minutes", REGISTRY["equipment_stopped"].params["minutes"]))
                if nowt - p["since"] >= mins * 60:
                    p["notified"].add(sub.chat_id)
                    await self.enqueue(
                        {
                            "kind": "equipment_state",
                            "state": "stopped",
                            "camera_id": cid,
                            "since": p["since"],
                            "ts": nowt,
                        },
                        [REGISTRY["equipment_stopped"]],
                        only_chats={sub.chat_id},
                    )

    async def enqueue(self, ev: dict, types: list, only_chats: set[int] | None = None) -> int:
        cid = ev.get("camera_id")
        n = 0
        async with get_sessionmaker()() as s:
            cams = dict((await s.execute(select(Camera.id, Camera.name))).all())
            ttl_h = float(await get_setting(s, "telegram.outbox_ttl_hours") or 24)
            for t in types:
                q = (
                    select(TelegramSubscription, TelegramChat)
                    .join(TelegramChat, TelegramChat.id == TelegramSubscription.chat_id)
                    .where(TelegramSubscription.message_type == t.code, TelegramChat.active.is_(True))
                )
                if t.per_camera:
                    q = q.where(TelegramSubscription.camera_id == cid)
                for sub, chat in (await s.execute(q)).all():
                    if only_chats is not None and chat.id not in only_chats:
                        continue
                    ctx = {"camera": cams.get(cid, "—"), "params": sub.params or {}}
                    text = t.render(ev, ctx)
                    image = None
                    if t.with_image and ev.get("event_id"):
                        image = f"count:{ev['event_id']}"
                    s.add(
                        NotificationOutbox(
                            chat_id=chat.id,
                            message_type=t.code,
                            text=text,
                            image_path=image,
                            status="pending",
                            expires_at=now() + timedelta(hours=ttl_h),
                        )
                    )
                    n += 1
            await s.commit()
        return n

    # ---------- smena hisoboti (jadval bo'yicha) ----------
    async def shift_report_loop(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.shift_report_tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("smena hisoboti")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), 20)

    async def shift_report_tick(self) -> None:
        """Har obuna (chat × kamera) uchun: smena boshidan har N daqiqada oraliq hisobot, smena tugaganda yakuniy.

        Holat Redis'da saqlanadi — servis qayta ishga tushsa takror yubormaydi.
        """
        now_dt = now()
        now_ts = now_dt.timestamp()
        async with get_sessionmaker()() as s:
            subs = (
                await s.execute(
                    select(TelegramSubscription, TelegramChat)
                    .join(TelegramChat, TelegramChat.id == TelegramSubscription.chat_id)
                    .where(TelegramSubscription.message_type == "shift_report", TelegramChat.active.is_(True))
                )
            ).all()
            state = await self.r.hgetall(SHIFT_REPORT_STATE)
            alive = {f"{sub.chat_id}:{sub.camera_id}" for sub, _ in subs}
            stale = [k for k in state if k not in alive]
            if stale:
                await self.r.hdel(SHIFT_REPORT_STATE, *stale)
            if not subs:
                return
            cur = None
            match = await self.shifts.resolve(s, now_dt)
            sdef = self.shifts.get(match.shift_id) if match else None
            if match and sdef:
                a, b = shift_bounds(sdef, match.shift_date)
                cur = {
                    "key": f"{match.shift_date.isoformat()}:{match.shift_id}",
                    "shift_id": match.shift_id,
                    "date": match.shift_date.isoformat(),
                    "name": match.shift_name,
                    "start": a.timestamp(),
                    "end": b.timestamp(),
                }

            for sub, chat in subs:
                k = f"{sub.chat_id}:{sub.camera_id}"
                interval = max(5.0, float((sub.params or {}).get("minutes", 60))) * 60
                st = json.loads(state[k]) if k in state else None
                if st and (cur is None or st["key"] != cur["key"]):
                    if st["end"] <= now_ts < st["end"] + FINAL_GRACE_SEC:
                        await self._send_shift_report(s, sub, chat, st, st["end"], final=True, interval=interval)
                    st = None
                if cur is None:
                    await self.r.hdel(SHIFT_REPORT_STATE, k)
                    continue
                slot = int((now_ts - cur["start"]) // interval)
                if st is None or st.get("interval") != interval:
                    st = {**cur, "slot": slot, "interval": interval}  # yangi smena/obuna — keyingi slotdan boshlab
                elif slot > st["slot"]:
                    await self._send_shift_report(s, sub, chat, st, now_ts, final=False, interval=interval)
                    st["slot"] = slot
                await self.r.hset(SHIFT_REPORT_STATE, k, json.dumps(st))

    async def _send_shift_report(self, s, sub, chat, st: dict, till: float, final: bool, interval: float) -> None:
        start = datetime.fromtimestamp(st["start"], UTC)
        end = datetime.fromtimestamp(till, UTC)
        summary = await camera_shift_summary(
            s,
            sub.camera_id,
            st["shift_id"],
            datetime.fromisoformat(st["date"]).date(),
            start,
            end,
            recent_from=None if final else end - timedelta(seconds=interval),
        )
        d = st["date"]
        ev = {
            "kind": "shift_report",
            "camera_id": sub.camera_id,
            "shift": st["name"],
            "shift_date": f"{d[8:10]}.{d[5:7]}",
            "start": st["start"],
            "end": till,
            "ts": time.time(),
            "final": final,
            "interval_min": int(interval // 60),
            "summary": summary,
        }
        await self.enqueue(ev, [REGISTRY["shift_report"]], only_chats={chat.id})

    # ---------- yuboruvchi ----------
    async def sender_loop(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            sent_any = False
            if self.state == "connected" and self.bot is not None:
                try:
                    sent_any = await self.send_batch()
                except Exception:
                    log.exception("yuborish sikli xatosi")
            await self.publish_stats()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), 0.3 if sent_any else 1.5)

    async def send_batch(self) -> bool:
        from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
        from aiogram.types import BufferedInputFile

        async with get_sessionmaker()() as s:
            # eskirganlar
            await s.execute(
                update(NotificationOutbox)
                .where(NotificationOutbox.status == "pending", NotificationOutbox.expires_at < now())
                .values(status="cancelled", last_error="Yashash muddati tugadi")
            )
            await s.commit()
            rows = (
                await s.execute(
                    select(NotificationOutbox, TelegramChat)
                    .join(TelegramChat, TelegramChat.id == NotificationOutbox.chat_id)
                    .where(NotificationOutbox.status == "pending", NotificationOutbox.next_attempt_at <= now())
                    .order_by(NotificationOutbox.id)
                    .limit(20)
                )
            ).all()
        sent = False
        for msg, chat in rows:
            gap = 3.0 if chat.type in ("group", "supergroup") else 1.0  # chat bo'yicha tezlik chegarasi
            if time.time() - self.last_sent.get(chat.id, 0) < gap:
                continue
            try:
                if msg.image_path and msg.image_path.startswith("count:"):
                    data = await self._count_image(int(msg.image_path.split(":")[1]))
                    if data:
                        await self.bot.send_photo(chat.chat_id, BufferedInputFile(data, "sanoq.jpg"), caption=msg.text)
                    else:
                        await self.bot.send_message(chat.chat_id, msg.text)
                else:
                    await self.bot.send_message(chat.chat_id, msg.text)
                self.last_sent[chat.id] = time.time()
                await self._mark(msg.id, status="sent", sent_at=now(), attempts=msg.attempts + 1, last_error=None)
                sent = True
            except TelegramRetryAfter as e:
                await self._mark(
                    msg.id,
                    next_attempt_at=now() + timedelta(seconds=e.retry_after + 1),
                    last_error=f"Telegram: {e.retry_after} s kuting",
                )
            except TelegramForbiddenError as e:
                await self.cancel_chat_messages(chat.chat_id, f"Bot chatdan chiqarilgan: {e.message}")
            except TelegramNetworkError as e:
                await self.set_status("no_internet", str(e)[:200])
                await self._mark(
                    msg.id,
                    attempts=msg.attempts + 1,
                    next_attempt_at=now() + timedelta(seconds=min(300, 5 * 2 ** min(msg.attempts, 6))),
                    last_error="Internet yo'q",
                )
                return sent
            except Exception as e:
                failed = msg.attempts + 1 >= 8
                await self._mark(
                    msg.id,
                    attempts=msg.attempts + 1,
                    status="failed" if failed else "pending",
                    last_error=str(e)[:300],
                    next_attempt_at=now() + timedelta(seconds=min(600, 10 * 2**msg.attempts)),
                )
        return sent

    async def _mark(self, mid: int, **vals) -> None:
        async with get_sessionmaker()() as s:
            await s.execute(update(NotificationOutbox).where(NotificationOutbox.id == mid).values(**vals))
            await s.commit()

    async def _count_image(self, event_id: int) -> bytes | None:
        from app.models.catalog import Product
        from app.services.render import render_snapshot

        async with get_sessionmaker()() as s:
            e = await s.get(CountEvent, event_id)
            if e is None or not e.snapshot_path:
                return None
            p = await s.get(Product, e.product_id) if e.product_id else None
        label = (p.name if p else "Noaniq") + (" (noaniq)" if e.status == "uncertain" else "")
        try:
            return await asyncio.to_thread(render_snapshot, e.snapshot_path, e.bbox, label)
        except Exception:
            return None

    async def publish_stats(self) -> None:
        from sqlalchemy import func

        async with get_sessionmaker()() as s:
            rows = dict(
                (
                    await s.execute(select(NotificationOutbox.status, func.count()).group_by(NotificationOutbox.status))
                ).all()
            )
        await self.r.hset("fcv:telegram:outbox", mapping={k: v for k, v in rows.items()} or {"pending": 0})
        await self.r.expire("fcv:telegram:outbox", 30)

    async def run(self, stop: asyncio.Event) -> None:
        await self.set_status("starting")
        tasks = [
            asyncio.create_task(self.polling_loop(stop)),
            asyncio.create_task(self.events_loop(stop)),
            asyncio.create_task(self.sender_loop(stop)),
            asyncio.create_task(self.shift_report_loop(stop)),
        ]
        await stop.wait()
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tasks, return_exceptions=True)
