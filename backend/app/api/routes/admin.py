import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, DbSession
from app.models import Event, Favorite, Order, Performance, Reservation
from app.schemas.admin import AdminPerformanceListOut, AdminPerformanceOut, PerformanceWriteIn

router = APIRouter(prefix="/admin/performances", tags=["admin"])


def _get_performance(db: Session, performance_id: str, *, lock: bool = False) -> Performance:
    stmt = select(Performance).where(Performance.id == performance_id)
    if lock:
        stmt = stmt.with_for_update()
    performance = db.scalar(stmt)
    if performance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    return performance


@router.get("", response_model=AdminPerformanceListOut)
def list_performances(
    user: AdminUser,
    db: DbSession,
    q: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=20),
    sort: Literal["date", "title", "price"] = "date",
    page: int = Query(1, ge=1, le=1_000_000),
    page_size: int = Query(10, ge=1, le=100),
):
    stmt = select(Performance)
    if category and category != "전체":
        stmt = stmt.where(Performance.category == category)
    if q and q.strip():
        # 관리자 검색에서는 %와 _도 검색어 그대로 취급합니다.
        keyword = q.strip()
        stmt = stmt.where(or_(
            Performance.title.contains(keyword, autoescape=True),
            Performance.venue.contains(keyword, autoescape=True),
        ))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = {"date": Performance.start_date, "title": Performance.title, "price": Performance.price}[sort]
    items = db.scalars(stmt.order_by(order, Performance.id).offset((page - 1) * page_size).limit(page_size)).all()
    return AdminPerformanceListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{performance_id}", response_model=AdminPerformanceOut)
def get_performance(performance_id: str, user: AdminUser, db: DbSession):
    return _get_performance(db, performance_id)


@router.post("", response_model=AdminPerformanceOut, status_code=status.HTTP_201_CREATED)
def create_performance(body: PerformanceWriteIn, user: AdminUser, db: DbSession):
    performance = Performance(id=str(uuid.uuid4()), **body.performance_values())
    db.add(performance)
    db.commit()
    return performance


@router.put("/{performance_id}", response_model=AdminPerformanceOut)
def update_performance(performance_id: str, body: PerformanceWriteIn, user: AdminUser, db: DbSession):
    performance = _get_performance(db, performance_id, lock=True)
    values = body.performance_values()
    # 기존 시연 데이터의 표시 기간과 예매 가능 기간이 달라도, 날짜를 바꾸지 않으면 표시 문구를 보존합니다.
    if body.start_date == performance.start_date and body.end_date == performance.end_date:
        values.pop("date_label")
    for field, value in values.items():
        setattr(performance, field, value)
    db.commit()
    return performance


@router.delete("/{performance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_performance(performance_id: str, user: AdminUser, db: DbSession) -> Response:
    performance = _get_performance(db, performance_id, lock=True)
    # 기존 예매·결제와 당시 공연 정보 스냅샷은 삭제하지 않습니다.
    has_orders = db.scalar(select(Order.id).where(Order.performance_id == performance_id).limit(1))
    has_reservations = db.scalar(select(Reservation.id).where(Reservation.performance_id == performance_id).limit(1))
    if has_orders or has_reservations:
        raise HTTPException(status.HTTP_409_CONFLICT, "예매 내역이 있는 공연은 삭제할 수 없습니다.")
    try:
        db.execute(delete(Favorite).where(Favorite.performance_id == performance_id))
        db.execute(delete(Event).where(Event.performance_id == performance_id))
        db.delete(performance)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "연결된 내역이 있어 공연을 삭제할 수 없습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
