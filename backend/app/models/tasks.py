from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin

TASK_TYPES = ("counting", "equipment")


class CameraTask(TimestampMixin, Base):
    __tablename__ = "camera_tasks"
    __table_args__ = (UniqueConstraint("camera_id", "task_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(12))  # counting | equipment
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class CountingConfig(TimestampMixin, Base):
    """Koordinatalar tahlil oqimi kadriga nisbatan 0–1."""

    __tablename__ = "counting_configs"

    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), primary_key=True)
    stream: Mapped[str] = mapped_column(String(4), default="main")  # shakllar qaysi oqimga chizilgan
    roi_polygon: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    line: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)  # [[ax, ay], [bx, by]]
    direction: Mapped[str] = mapped_column(String(8), default="a_to_b")  # a_to_b | b_to_a | both
    reverse_policy: Mapped[str] = mapped_column(String(10), default="ignore")  # ignore | subtract | separate
    max_angle: Mapped[int] = mapped_column(Integer, default=60)
    track_point: Mapped[str] = mapped_column(String(14), default="center")  # center | bottom_center
    inference_fps: Mapped[float] = mapped_column(Float, default=5.0)
    min_track_frames: Mapped[int] = mapped_column(Integer, default=3)
    min_distance: Mapped[float] = mapped_column(Float, default=0.01)  # kadr diagonaliga nisbatan
    conf_threshold: Mapped[float] = mapped_column(Float, default=0.35)
    uncertain_margin: Mapped[float] = mapped_column(Float, default=0.2)  # g'olib va 2-o'rin farqi
    min_winner_score: Mapped[float] = mapped_column(Float, default=0.5)  # o'rtacha ishonch


class EquipmentConfig(TimestampMixin, Base):
    __tablename__ = "equipment_configs"

    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), primary_key=True)
    stream: Mapped[str] = mapped_column(String(4), default="main")
    roi_polygon: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    control_zone: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    exclude_zones: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    motion_threshold: Mapped[float] = mapped_column(Float, default=2.0)  # harakat foizi
    min_on_sec: Mapped[float] = mapped_column(Float, default=3.0)
    min_off_sec: Mapped[float] = mapped_column(Float, default=10.0)
    cycle_mode: Mapped[str] = mapped_column(String(8), default="home")  # home | peaks | off
    returns_per_cycle: Mapped[int] = mapped_column(Integer, default=1)  # K
    home_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # tayanch kadr fayli
    home_exit_threshold: Mapped[float] = mapped_column(Float, default=12.0)  # farq % — "chiqdi"
    home_return_threshold: Mapped[float] = mapped_column(Float, default=6.0)  # farq % — "qaytdi"
    peak_min_height: Mapped[float] = mapped_column(Float, default=5.0)
    peak_min_distance_sec: Mapped[float] = mapped_column(Float, default=0.5)
    reference_cycle_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_reference: Mapped[bool] = mapped_column(Boolean, default=True)
    micro_stop_factor: Mapped[float] = mapped_column(Float, default=1.5)
