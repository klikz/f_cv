from typing import Annotated

from fastapi import Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.redis import get_redis

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def redis_dep() -> Redis:
    return get_redis()


RedisDep = Annotated[Redis, Depends(redis_dep)]


def not_found(what: str = "Topilmadi") -> HTTPException:
    return HTTPException(404, what)
