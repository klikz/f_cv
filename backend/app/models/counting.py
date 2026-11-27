from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CountingConfigProduct(Base):
    """Kameraga biriktirilgan faol mahsulotlar (liniyada ketadigan 5–6 model)."""

    __tablename__ = "counting_config_products"
    __table_args__ = (UniqueConstraint("camera_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True
    )  # bo'sh — mahsulotning faol versiyasi
    size_min: Mapped[float | None] = mapped_column(Float, nullable=True)  # bbox maydoni (0–1) oralig'i
    size_max: Mapped[float | None] = mapped_column(Float, nullable=True)


class CountEvent(Base):
    __tablename__ = "count_events"
    __table_args__ = (
        Index("ix_count_events_camera_ts", "camera_id", "ts"),
        Index("ix_count_events_shift", "shift_date", "shift_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    original_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(10), index=True)  # confirmed | uncertain | corrected | cancelled
    candidates: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # [{product_id, score}]
    direction: Mapped[str] = mapped_column(String(8), default="forward")  # forward | reverse
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    shift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shift_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManualCount(Base):
    __tablename__ = "manual_counts"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
