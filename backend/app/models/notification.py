from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    booking_reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    favorite_updates: Mapped[bool] = mapped_column(Boolean, default=False)
