from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.config import MAX_QUANTITY

# MySQL DATETIME·SQLite는 시간대를 저장하지 않아 DB에서 읽으면 시간대 없는 값이 됩니다.
# 서버는 항상 UTC로 저장하므로 응답에서는 UTC(+00:00)를 붙여 화면이 한국 시간으로 바르게 바꾸게 합니다.
UtcDatetime = Annotated[datetime, AfterValidator(lambda v: v if v.tzinfo else v.replace(tzinfo=timezone.utc))]


class ReservationIn(BaseModel):
    """예매 요청. 가격·상태·사용자·시각은 서버가 정하므로 받지 않습니다(보내도 무시)."""

    performance_id: str
    performance_date: date
    session_time: str
    seat_grade: Literal["STANDARD", "PREMIUM"]
    quantity: int = Field(ge=1, le=MAX_QUANTITY)
    # 예매 창을 열 때 화면이 만든 UUID. 같은 키로 다시 보내면 기존 예매를 돌려줍니다(중복 방지).
    request_key: UUID


class ReservationOut(BaseModel):
    """예매 + 결제 정보를 합친 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    mbti: str
    performance_id: str
    performance_title: str
    category: str
    venue: str
    performance_date: date
    session_time: str
    seat_grade: str
    quantity: int
    unit_price: int
    amount: int
    currency: str
    status: str  # REQUESTED | CONFIRMED | CANCELLED
    created_at: UtcDatetime
    updated_at: UtcDatetime
    cancelled_at: UtcDatetime | None
    payment_id: str
    payment_status: str  # PENDING | COMPLETED | CANCELLED
    requested_at: UtcDatetime
    completed_at: UtcDatetime | None
    payment_cancelled_at: UtcDatetime | None
    is_mock: bool = True


class PaymentOut(BaseModel):
    """결제 내역. 어떤 예매의 결제인지 알 수 있도록 예매 요약을 함께 담습니다."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    reservation_id: str
    performance_id: str
    performance_title: str
    performance_date: date
    session_time: str
    quantity: int
    amount: int
    currency: str
    status: str  # PENDING | COMPLETED | CANCELLED
    requested_at: UtcDatetime
    completed_at: UtcDatetime | None
    cancelled_at: UtcDatetime | None
    is_mock: bool = True
