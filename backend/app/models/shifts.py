from datetime import datetime, time

from sqlalchemy import DateTime, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Shift(TimestampMixin, Base):
    """Smena. Bir xil `effective_from` ga ega qatorlar bitta smenalar to'plami (versiyasi).

    O'zgartirish faqat yangi `effective_from` bilan yangi to'plam qo'shish orqali —
    eski hodisalarga ta'sir qilmaydi.
    """

    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
