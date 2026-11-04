from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class EventIn(BaseModel):
    performance_id: str
    # 화면에서 보낼 수 있는 탐색 이벤트. 예매·결제·취소 이벤트는 서버가 직접 기록합니다.
    type: Literal["performance_view", "booking_started"] = "performance_view"


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    mbti: str | None
    type: str
    performance_id: str
    category: str
    reservation_id: str | None = None
    created_at: datetime
