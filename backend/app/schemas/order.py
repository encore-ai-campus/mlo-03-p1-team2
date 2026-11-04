from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import MAX_QUANTITY, PAYMENT_METHODS

PaymentMethod = Literal[PAYMENT_METHODS]  # type: ignore[valid-type]


class OrderIn(BaseModel):
    performance_id: str
    performance_date: date
    session_time: str
    seat_grade: Literal["STANDARD", "PREMIUM"]
    quantity: int = Field(ge=1, le=MAX_QUANTITY)
    payment_method: PaymentMethod


class OrderOut(BaseModel):
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
    payment_method: str
    status: str
    is_mock: bool
    created_at: datetime
