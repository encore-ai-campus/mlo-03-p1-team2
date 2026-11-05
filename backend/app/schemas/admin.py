import re
from datetime import date
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import CATEGORIES, MAX_PERFORMANCE_PRICE
from app.schemas.performance import PerformanceOut

POSTER_STYLES = ("city", "opera", "art", "jazz", "sport", "classic", "theater", "dance")


class PerformanceWriteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    category: str = Field(max_length=20)
    venue: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    price: int = Field(strict=True, ge=0, le=MAX_PERFORMANCE_PRICE)
    slots: list[str] = Field(min_length=1, max_length=24)
    image: str = Field(min_length=1, max_length=500)
    english: str = Field(default="", max_length=200)
    sub: str = Field(default="", max_length=200)
    style: str = Field(default="city", max_length=50)
    badge: str = Field(default="", max_length=100)
    tag: str = Field(default="", max_length=100)

    @field_validator("title", "venue", "english", "sub", "badge", "tag")
    @classmethod
    def strip_text(cls, value: str, info) -> str:
        value = value.strip()
        if info.field_name in ("title", "venue") and not value:
            raise ValueError("공연명과 공연장을 입력해 주세요.")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("올바른 공연 카테고리를 선택해 주세요.")
        return value

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        if value not in POSTER_STYLES:
            raise ValueError("올바른 포스터 스타일을 선택해 주세요.")
        return value

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("https://"):
            url = urlsplit(value)
            if url.hostname != "images.unsplash.com":
                raise ValueError("Unsplash 이미지 주소를 입력해 주세요.")
            value = url.path.removeprefix("/")
        if not re.fullmatch(r"photo-[A-Za-z0-9-]+", value) or len(value) > 200:
            raise ValueError("https://images.unsplash.com/photo-… 형식의 이미지 주소를 입력해 주세요.")
        return value

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, value: list[str]) -> list[str]:
        value = [slot.strip() for slot in value]
        if any(not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", slot) for slot in value):
            raise ValueError("회차는 00:00~23:59 형식으로 입력해 주세요.")
        if len(value) != len(set(value)):
            raise ValueError("같은 회차를 중복해서 입력할 수 없습니다.")
        return sorted(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "PerformanceWriteIn":
        if self.end_date < self.start_date:
            raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
        if (self.end_date - self.start_date).days >= 366:
            raise ValueError("한 공연의 예매 가능 기간은 최대 366일입니다.")
        return self

    def performance_values(self) -> dict:
        values = self.model_dump(exclude={"end_date"})
        values["days"] = (self.end_date - self.start_date).days + 1
        values["date_label"] = f"{self.start_date:%Y.%m.%d} - {self.end_date:%Y.%m.%d}"
        values["english"] = self.english or self.title
        return values


class AdminPerformanceOut(PerformanceOut):
    end_date: date


class AdminPerformanceListOut(BaseModel):
    items: list[AdminPerformanceOut]
    total: int
    page: int
    page_size: int
