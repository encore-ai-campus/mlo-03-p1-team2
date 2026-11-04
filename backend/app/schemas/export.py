from datetime import datetime

from pydantic import BaseModel

from app.schemas.event import EventOut
from app.schemas.order import OrderOut
from app.schemas.reservation import ReservationOut
from app.schemas.user import UserOut


class ExportOut(BaseModel):
    exported_at: datetime
    profile: UserOut
    orders: list[OrderOut]
    reservations: list[ReservationOut]
    events: list[EventOut]
    favorites: list[str]
