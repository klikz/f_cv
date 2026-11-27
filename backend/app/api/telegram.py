"""Telegram: bot holati, token, chatlar, obuna matritsasi, outbox, sinov xabari."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from app.api.deps import RedisDep, SessionDep, not_found
from app.core import keys
from app.core.config import get_settings
from app.models.cameras import Camera
from app.models.telegram import NotificationOutbox, TelegramChat, TelegramSubscription
from app.services.settings_store import get_setting, set_setting
from telegram.registry import REGISTRY, TEST, describe

router = APIRouter(prefix="/telegram", tags=["telegram"])

STATE_LABEL = {
    "connected": "Ulangan",
    "no_internet": "Internet yo'q",
    "bad_token": "Token xato",
    "no_token": "Token kiritilmagan",
    "starting": "Ishga tushmoqda",
}


@router.get("/status")
async def status(session: SessionDep, redis: RedisDep) -> dict:
    st = await redis.hgetall(keys.TELEGRAM_STATUS)
    ob = await redis.hgetall("fcv:telegram:outbox")
    token = await get_setting(session, "telegram.token") or get_settings().telegram_bot_token
    state = st.get("state") or "offline"
    return {
        "state": state,
        "label": STATE_LABEL.get(state, "Servis ishlamayapti"),
        "error": st.get("error") or None,
        "username": st.get("username") or None,
        "has_token": bool(token),
        "outbox": {k: int(v) for k, v in ob.items()},
        "types": describe(),
    }


class TokenIn(BaseModel):
    token: str = Field(default="", max_length=200)


@router.put("/token")
async def set_token(data: TokenIn, session: SessionDep) -> dict:
    t = data.token.strip()
    if t and ":" not in t:
        raise HTTPException(422, "Token formati noto'g'ri (masalan 123456:ABC...)")
    await set_setting(session, "telegram.token", t)
    return {"has_token": bool(t)}


class ChatOut(BaseModel):
    id: int
    chat_id: int
    title: str
    type: str
    active: bool
    subscriptions: int
    created_at: datetime


@router.get("/chats", response_model=list[ChatOut])
async def chats(session: SessionDep) -> list[ChatOut]:
    cnt = dict(
        (
            await session.execute(
                select(TelegramSubscription.chat_id, func.count()).group_by(TelegramSubscription.chat_id)
            )
        ).all()
    )
    rows = (
        await session.execute(select(TelegramChat).order_by(TelegramChat.active.desc(), TelegramChat.title))
    ).scalars()
    return [
        ChatOut(
            id=c.id,
            chat_id=c.chat_id,
            title=c.title,
            type=c.type,
            active=c.active,
            subscriptions=cnt.get(c.id, 0),
            created_at=c.created_at,
        )
        for c in rows
    ]


class Sub(BaseModel):
    camera_id: int | None
    message_type: str
    params: dict = Field(default_factory=dict)


class Matrix(BaseModel):
    items: list[Sub]


@router.get("/chats/{chat_id}/subscriptions", response_model=Matrix)
async def get_subs(chat_id: int, session: SessionDep) -> Matrix:
    rows = (
        await session.execute(select(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    ).scalars()
    return Matrix(items=[Sub(camera_id=r.camera_id, message_type=r.message_type, params=r.params or {}) for r in rows])


@router.put("/chats/{chat_id}/subscriptions", response_model=Matrix)
async def put_subs(chat_id: int, data: Matrix, session: SessionDep) -> Matrix:
    if await session.get(TelegramChat, chat_id) is None:
        raise not_found("Chat topilmadi")
    cams = set((await session.execute(select(Camera.id))).scalars())
    await session.execute(delete(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    seen = set()
    for it in data.items:
        t = REGISTRY.get(it.message_type)
        if t is None:
            raise HTTPException(422, f"Noma'lum xabar turi: {it.message_type}")
        cam = it.camera_id if t.per_camera else None
        if t.per_camera and cam not in cams:
            continue
        key = (cam, it.message_type)
        if key in seen:
            continue
        seen.add(key)
        session.add(
            TelegramSubscription(
                chat_id=chat_id, camera_id=cam, task_type=t.task, message_type=t.code, params={**t.params, **it.params}
            )
        )
    await session.commit()
    return await get_subs(chat_id, session)


@router.post("/chats/{chat_id}/test")
async def send_test(chat_id: int, session: SessionDep) -> dict:
    chat = await session.get(TelegramChat, chat_id)
    if chat is None:
        raise not_found("Chat topilmadi")
    if not chat.active:
        raise HTTPException(409, "Chat faol emas (bot chatdan chiqarilgan)")
    m = NotificationOutbox(
        chat_id=chat.id,
        message_type="test",
        text=TEST.render({}, {}),
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(m)
    await session.commit()
    return {"queued": m.id}


@router.post("/chats/{chat_id}/shift-report/{camera_id}")
async def send_shift_report_now(chat_id: int, camera_id: int, redis: RedisDep) -> dict:
    """ "Darhol": joriy holat bo'yicha smena hisobotini shu chatga navbatga qo'yish."""
    from telegram.service import TelegramService

    try:
        mid = await TelegramService(redis).send_shift_report_now(chat_id, camera_id)
    except LookupError as e:
        raise not_found(str(e)) from e
    except PermissionError as e:
        raise HTTPException(409, str(e)) from e
    return {"queued": mid}


@router.get("/outbox")
async def outbox(session: SessionDep, limit: int = 50) -> list[dict]:
    names = dict((await session.execute(select(TelegramChat.id, TelegramChat.title))).all())
    rows = (
        await session.execute(select(NotificationOutbox).order_by(NotificationOutbox.id.desc()).limit(limit))
    ).scalars()
    return [
        {
            "id": r.id,
            "chat": names.get(r.chat_id),
            "type": r.message_type,
            "status": r.status,
            "attempts": r.attempts,
            "error": r.last_error,
            "created_at": r.created_at,
            "sent_at": r.sent_at,
            "text": r.text[:200],
        }
        for r in rows
    ]
