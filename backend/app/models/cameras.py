from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    connection_type: Mapped[str] = mapped_column(String(10), default="rtsp")  # rtsp | onvif
    main_rtsp_url: Mapped[str] = mapped_column(Text)
    sub_rtsp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_stream: Mapped[str] = mapped_column(String(4), default="main")  # main | sub
    fov_match: Mapped[bool] = mapped_column(Boolean, default=False)

    onvif_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onvif_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onvif_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    onvif_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onvif_manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    onvif_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    onvif_serial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    onvif_main_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)
    onvif_sub_profile: Mapped[str | None] = mapped_column(String(100), nullable=True)

    streams: Mapped[list["CameraStream"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan", lazy="selectin"
    )


class CameraStream(Base):
    __tablename__ = "camera_streams"
    __table_args__ = (UniqueConstraint("camera_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(4))  # main | sub
    codec: Mapped[str | None] = mapped_column(String(20), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="offline")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    camera: Mapped[Camera] = relationship(back_populates="streams")


class CoverageGap(Base):
    """Sanalmagan oraliqlar: kamera uzilgan, train ketgan yoki servis o'chgan vaqt."""

    __tablename__ = "coverage_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_type: Mapped[str | None] = mapped_column(String(12), nullable=True)
    reason: Mapped[str] = mapped_column(String(12))  # camera | train | service
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
