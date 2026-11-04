from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import DbSession
from app.core.config import PURCHASE_EVENT_TYPES
from app.models import Event, Performance
from app.schemas.performance import PerformanceDetailOut, PerformanceOut, RankingOut

router = APIRouter(prefix="/performances", tags=["performances"])


def _event_counts(*event_types: str):
    return (
        select(Event.performance_id, func.count().label("n"))
        .where(Event.type.in_(event_types))
        .group_by(Event.performance_id)
        .subquery()
    )


@router.get("", response_model=list[PerformanceOut])
def list_performances(
    db: DbSession,
    category: str | None = None,
    q: str | None = Query(None, max_length=100),
    sort: Literal["popular", "date", "price"] = "popular",
):
    stmt = select(Performance)
    if category and category != "전체":
        stmt = stmt.where(Performance.category == category)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Performance.title.like(like), Performance.venue.like(like), Performance.category.like(like))
        )
    if sort == "date":
        stmt = stmt.order_by(Performance.start_date, Performance.id)
    elif sort == "price":
        stmt = stmt.order_by(Performance.price, Performance.id)
    else:
        buys = _event_counts(*PURCHASE_EVENT_TYPES)
        stmt = stmt.outerjoin(buys, buys.c.performance_id == Performance.id).order_by(
            func.coalesce(buys.c.n, 0).desc(), Performance.id
        )
    return db.scalars(stmt).all()


@router.get("/ranking", response_model=list[RankingOut])
def ranking(db: DbSession, limit: int = Query(5, ge=1, le=50)):
    buys = _event_counts(*PURCHASE_EVENT_TYPES)
    views = _event_counts("performance_view")
    purchases = func.coalesce(buys.c.n, 0)
    view_count = func.coalesce(views.c.n, 0)
    rows = db.execute(
        select(Performance, purchases, view_count)
        .outerjoin(buys, buys.c.performance_id == Performance.id)
        .outerjoin(views, views.c.performance_id == Performance.id)
        .order_by(purchases.desc(), view_count.desc(), Performance.id)
        .limit(limit)
    ).all()
    return [
        RankingOut(**PerformanceOut.model_validate(p).model_dump(), purchases=pc, views=vc)
        for p, pc, vc in rows
    ]


@router.get("/{performance_id}", response_model=PerformanceDetailOut)
def get_performance(performance_id: str, db: DbSession):
    p = db.get(Performance, performance_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    return p
