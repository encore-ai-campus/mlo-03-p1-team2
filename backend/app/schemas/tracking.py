from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.config import TRACKING_EVENT_TYPES, TRACKING_MAX_BATCH

EventType = Literal[TRACKING_EVENT_TYPES]  # type: ignore[valid-type]
ShortText = Annotated[str, StringConstraints(max_length=500)]
PropValue = str | int | float | bool | None

MAX_PROPS = 20
MAX_PROP_KEY = 40
MAX_PROP_TEXT = 500


class PageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: ShortText
    referrer: ShortText = ""


class TrackingEventIn(BaseModel):
    """프론트엔드가 보내는 행동 이벤트 1건."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    type: EventType
    occurred_at: datetime
    session_id: UUID
    anonymous_id: UUID
    page: PageIn
    props: dict[str, PropValue] = Field(default_factory=dict)
    schema_version: int = Field(ge=1, le=100)

    @field_validator("props")
    @classmethod
    def _small_flat_props(cls, props: dict[str, PropValue]) -> dict[str, PropValue]:
        # 한 단계짜리 작은 값만 받습니다 (중첩 객체·긴 문자열로 저장소를 채우지 못하게).
        if len(props) > MAX_PROPS:
            raise ValueError(f"props 는 최대 {MAX_PROPS}개까지 보낼 수 있습니다.")
        for key, value in props.items():
            if not key or len(key) > MAX_PROP_KEY:
                raise ValueError(f"props 키는 1~{MAX_PROP_KEY}자여야 합니다.")
            if isinstance(value, str) and len(value) > MAX_PROP_TEXT:
                raise ValueError(f"props 값은 {MAX_PROP_TEXT}자 이내여야 합니다.")
        return props


class TrackingBatchIn(BaseModel):
    events: list[TrackingEventIn] = Field(min_length=1, max_length=TRACKING_MAX_BATCH)


class TrackingBatchOut(BaseModel):
    accepted: int
    duplicates: int
