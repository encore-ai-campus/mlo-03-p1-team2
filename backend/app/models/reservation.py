import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Reservation(Base):
    """예매. REQUESTED(예매 요청) → CONFIRMED(예매 완료) / CANCELLED(예매 취소)"""

    __tablename__ = "reservations"
    # 같은 사용자의 같은 요청 키는 한 번만 저장되어, 재시도해도 예매가 중복 생성되지 않습니다.
    __table_args__ = (UniqueConstraint("user_id", "request_key", name="uq_reservations_user_request_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    performance_id: Mapped[str] = mapped_column(ForeignKey("performances.id"), index=True)
    # 예매 당시 공연 정보·MBTI 스냅샷
    performance_title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20))
    venue: Mapped[str] = mapped_column(String(200))
    mbti: Mapped[str] = mapped_column(String(4))
    performance_date: Mapped[date] = mapped_column(Date)
    session_time: Mapped[str] = mapped_column(String(5))
    seat_grade: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="REQUESTED")
    request_key: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment: Mapped["Payment"] = relationship(back_populates="reservation", uselist=False, lazy="joined")

    # 응답(ReservationOut)에서 결제 정보를 평평하게 펼쳐 보여주기 위한 속성
    @property
    def payment_id(self) -> str:
        return self.payment.id

    @property
    def payment_status(self) -> str:
        return self.payment.status

    @property
    def currency(self) -> str:
        return self.payment.currency

    @property
    def requested_at(self) -> datetime:
        return self.payment.requested_at

    @property
    def completed_at(self) -> datetime | None:
        return self.payment.completed_at

    @property
    def payment_cancelled_at(self) -> datetime | None:
        return self.payment.cancelled_at


class Payment(Base):
    """모의 결제. PENDING(결제 대기) → COMPLETED(결제 완료) / CANCELLED(결제 취소)"""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), unique=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    status: Mapped[str] = mapped_column(String(10), default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reservation: Mapped[Reservation] = relationship(back_populates="payment")


class StatusHistory(Base):
    """예매·결제 상태 변경 이력 (entity: reservation | payment)"""

    __tablename__ = "status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    reservation_id: Mapped[str] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    entity: Mapped[str] = mapped_column(String(20))
    from_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    to_status: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
