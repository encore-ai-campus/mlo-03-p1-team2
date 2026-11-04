from datetime import date

from pydantic import BaseModel, ConfigDict


class PerformanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    title: str
    english: str
    sub: str
    image: str
    style: str
    venue: str
    date_label: str
    start_date: date
    days: int
    price: int
    badge: str
    tag: str
    slots: list[str]


class PerformanceDetailOut(PerformanceOut):
    available_dates: list[date]


class RankingOut(PerformanceOut):
    purchases: int
    views: int
