from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class NotificationSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_reminders: StrictBool
    favorite_updates: StrictBool


class NotificationSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_reminders: bool = False
    favorite_updates: bool = False


class NotificationOut(BaseModel):
    id: str
    kind: Literal["booking", "favorite"]
    performance_id: str
    title: str
    date: date
    message: str
    reservation_id: str | None = None


class TasteCounts(BaseModel):
    views: int = 0
    favorites: int = 0
    bookings: int = 0


class CategoryTaste(TasteCounts):
    category: str
    peer_favorites: int = 0


class TasteReportOut(BaseModel):
    mbti: str
    totals: TasteCounts
    categories: list[CategoryTaste]
    peer_users: int
