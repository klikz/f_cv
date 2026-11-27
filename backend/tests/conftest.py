"""Testlar: alohida `f_cv_test` bazasi va Redis 15-bazasi."""

import os

os.environ["FCV_DATABASE_URL"] = os.environ.get(
    "FCV_TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/f_cv_test"
)
os.environ["FCV_REDIS_URL"] = "redis://localhost:6379/15"
os.environ["FCV_DATA_DIR"] = "/tmp/fcv-test-data"

import pytest
from sqlalchemy import text

from app.core.config import get_settings

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    from alembic.config import Config

    from alembic import command

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["FCV_DATABASE_URL"])
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def db():
    from app.core.db import Base, get_engine, get_sessionmaker

    eng = get_engine()
    async with eng.begin() as conn:
        names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables if t.name != "shifts")
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    async with get_sessionmaker()() as s:
        yield s


@pytest.fixture
async def redis():
    from app.core.redis import get_redis

    r = get_redis()
    await r.flushdb()
    yield r
    await r.flushdb()


@pytest.fixture
async def client(db, redis):
    import httpx

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
