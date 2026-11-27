"""Sozlamalar: `.env` (repo ildizida) va muhit o'zgaruvchilaridan o'qiladi."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_SUBDIRS = ("snapshots", "datasets", "models", "engines", "logs")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FCV_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/f_cv"
    test_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/f_cv_test"
    redis_url: str = "redis://localhost:6379/5"

    data_dir: Path = Path("data")

    api_host: str = "0.0.0.0"
    api_port: int = 8100

    telegram_bot_token: str = ""
    decode_backend: Literal["auto", "vaapi", "nvdec", "cpu"] = "auto"

    log_level: str = "INFO"
    timezone: str = "Asia/Tashkent"

    heartbeat_interval_sec: float = Field(default=2.0, gt=0)
    heartbeat_ttl_sec: int = Field(default=10, gt=0)

    @property
    def data_path(self) -> Path:
        p = self.data_dir
        return p if p.is_absolute() else REPO_ROOT / p

    def data_subdir(self, name: str) -> Path:
        return self.data_path / name

    @property
    def frontend_dist(self) -> Path:
        return REPO_ROOT / "frontend" / "dist"

    def ensure_data_dirs(self) -> None:
        for name in DATA_SUBDIRS:
            self.data_subdir(name).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
