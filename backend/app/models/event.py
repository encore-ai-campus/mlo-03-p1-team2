import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Event(Base):
    __tablename__ = "events"
    # 인기순 정렬·랭킹은 type으로 거른 뒤 performance_id별로 셉니다. 두 컬럼을 한 인덱스에 두면
    # 테이블 본문을 읽지 않고 인덱스만으로 셀 수 있습니다. type 단독 조회도 이 인덱스의 앞부분으로 처리됩니다.
    __table_args__ = (Index("ix_events_type_performance_id", "type", "performance_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    mbti: Mapped[str | None] = mapped_column(String(4), nullable=True)
    type: Mapped[str] = mapped_column(String(30))
    performance_id: Mapped[str] = mapped_column(ForeignKey("performances.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    # 예매 관련 이벤트(reservation_requested·payment_completed·reservation_cancelled)일 때 연결된 예매
    reservation_id: Mapped[str | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
