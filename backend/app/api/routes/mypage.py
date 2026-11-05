from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import CATEGORIES
from app.models import Event, Favorite, Order, Payment, Performance, Reservation, User
from app.models.notification import NotificationSettings
from app.schemas.mypage import (
    CategoryTaste, NotificationOut, NotificationSettingsIn, NotificationSettingsOut,
    TasteCounts, TasteReportOut,
)

router = APIRouter(prefix="/users/me", tags=["mypage"])
KST = timezone(timedelta(hours=9))


@router.get("/taste-report", response_model=TasteReportOut)
def taste_report(user: CurrentUser, db: DbSession):
    categories = {c: CategoryTaste(category=c) for c in CATEGORIES}

    queries = [
        ("views", select(Event.category, func.count()).where(
            Event.user_id == user.id, Event.type == "performance_view"
        ).group_by(Event.category)),
        ("favorites", select(Performance.category, func.count()).join(
            Favorite, Favorite.performance_id == Performance.id
        ).where(Favorite.user_id == user.id).group_by(Performance.category)),
        ("bookings", select(Reservation.category, func.count()).join(Payment).where(
            Reservation.user_id == user.id, Reservation.status == "CONFIRMED",
            Payment.status == "COMPLETED"
        ).group_by(Reservation.category)),
        ("bookings", select(Order.category, func.count()).where(
            Order.user_id == user.id, Order.status == "MOCK_PAID"
        ).group_by(Order.category)),
        ("peer_favorites", select(Performance.category, func.count()).join(
            Favorite, Favorite.performance_id == Performance.id
        ).join(User, User.id == Favorite.user_id).where(
            User.mbti == user.mbti, User.id != user.id
        ).group_by(Performance.category)),
    ]
    for field, query in queries:
        for category, count in db.execute(query):
            if category in categories:
                row = categories[category]
                setattr(row, field, getattr(row, field) + count)
    peers = db.scalar(select(func.count(func.distinct(User.id))).join(
        Favorite, Favorite.user_id == User.id
    ).where(User.mbti == user.mbti, User.id != user.id))
    totals = TasteCounts(**{
        field: sum(getattr(c, field) for c in categories.values())
        for field in ("views", "favorites", "bookings")
    })
    return TasteReportOut(mbti=user.mbti, totals=totals, categories=list(categories.values()), peer_users=peers)


@router.get("/notification-settings", response_model=NotificationSettingsOut)
def notification_settings(user: CurrentUser, db: DbSession):
    return db.get(NotificationSettings, user.id) or NotificationSettingsOut()


@router.put("/notification-settings", response_model=NotificationSettingsOut)
def save_notification_settings(body: NotificationSettingsIn, user: CurrentUser, db: DbSession):
    settings = db.get(NotificationSettings, user.id)
    if settings is None:
        settings = NotificationSettings(user_id=user.id)
        db.add(settings)
    settings.booking_reminders = body.booking_reminders
    settings.favorite_updates = body.favorite_updates
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user: CurrentUser, db: DbSession):
    settings = db.get(NotificationSettings, user.id)
    if settings is None:
        return []
    now = datetime.now(KST)
    today = now.date()
    until = today + timedelta(days=7)
    items = []
    if settings.booking_reminders:
        rows = db.scalars(select(Reservation).join(Payment).where(
            Reservation.user_id == user.id, Reservation.status == "CONFIRMED",
            Payment.status == "COMPLETED", Reservation.performance_date.between(today, until)
        )).unique().all()
        for row in rows:
            starts = datetime.fromisoformat(f"{row.performance_date}T{row.session_time}").replace(tzinfo=KST)
            if starts < now:
                continue
            items.append(NotificationOut(
                id=f"booking-{row.id}", kind="booking", performance_id=row.performance_id,
                reservation_id=row.id, title=row.performance_title, date=row.performance_date,
                message=f"{row.performance_date} {row.session_time} · {row.venue} · {row.quantity}매",
            ))
    if settings.favorite_updates:
        shows = db.scalars(select(Performance).join(Favorite).where(
            Favorite.user_id == user.id, Performance.start_date <= until
        )).all()
        for show in shows:
            end = show.start_date + timedelta(days=show.days - 1)
            if end < today:
                continue
            items.append(NotificationOut(
                id=f"favorite-{show.id}", kind="favorite", performance_id=show.id,
                title=show.title, date=max(today, show.start_date),
                message=f"찜한 공연이 {'진행 중이에요' if show.start_date <= today else '곧 시작해요'}. {show.date_label} · {show.venue}",
            ))
    return sorted(items, key=lambda item: (item.date, item.id))
