from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class EventIn(BaseModel):
    performance_id: str
    type: Literal["performance_view"] = "performance_view"


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    mbti: str | None
    type: str
    performance_id: str
    category: str
    created_at: datetime
