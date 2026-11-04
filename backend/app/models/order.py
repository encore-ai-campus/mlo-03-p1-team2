import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    performance_id: Mapped[str] = mapped_column(ForeignKey("performances.id"), index=True)
    # Snapshot fields kept for history, matching the frontend order object
    mbti: Mapped[str] = mapped_column(String(4))
    performance_title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20))
    venue: Mapped[str] = mapped_column(String(200))
    performance_date: Mapped[date] = mapped_column(Date)
    session_time: Mapped[str] = mapped_column(String(5))
    seat_grade: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    payment_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="MOCK_PAID")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
