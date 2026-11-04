import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    mbti: Mapped[str | None] = mapped_column(String(4), nullable=True)
    type: Mapped[str] = mapped_column(String(30), index=True)
    performance_id: Mapped[str] = mapped_column(ForeignKey("performances.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    # 예매 관련 이벤트(reservation_requested·payment_completed·reservation_cancelled)일 때 연결된 예매
    reservation_id: Mapped[str | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
