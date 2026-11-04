from datetime import date, timedelta

from sqlalchemy import JSON, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Performance(Base):
    __tablename__ = "performances"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(200))
    english: Mapped[str] = mapped_column(String(200))
    sub: Mapped[str] = mapped_column(String(200))
    image: Mapped[str] = mapped_column(String(200))
    style: Mapped[str] = mapped_column(String(50))
    venue: Mapped[str] = mapped_column(String(200))
    date_label: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    badge: Mapped[str] = mapped_column(String(100))
    tag: Mapped[str] = mapped_column(String(100))
    slots: Mapped[list[str]] = mapped_column(JSON)

    @property
    def available_dates(self) -> list[date]:
        return [self.start_date + timedelta(days=i) for i in range(self.days)]
