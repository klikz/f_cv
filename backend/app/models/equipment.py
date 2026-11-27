from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EquipmentInterval(Base):
    __tablename__ = "equipment_intervals"
    __table_args__ = (Index("ix_equipment_intervals_camera_start", "camera_id", "start_ts"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(8))  # running | stopped | unknown
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shift_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)


class CycleEvent(Base):
    __tablename__ = "cycle_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration: Mapped[float] = mapped_column(Float)
    deviation: Mapped[float | None] = mapped_column(Float, nullable=True)  # etalondan, soniya
    is_micro_stop: Mapped[bool] = mapped_column(Boolean, default=False)
    shift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shift_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)


class EquipmentMinuteStat(Base):
    __tablename__ = "equipment_minute_stats"

    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), primary_key=True)
    minute: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    avg_motion: Mapped[float] = mapped_column(Float)
    run_seconds: Mapped[float] = mapped_column(Float)
