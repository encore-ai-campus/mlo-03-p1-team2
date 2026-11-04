from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import PREMIUM_SURCHARGE
from app.models import Event, Order, Performance
from app.schemas.order import OrderIn, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


def _invalid(msg: str) -> HTTPException:
    return HTTPException(422, msg)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(body: OrderIn, user: CurrentUser, db: DbSession):
    p = db.get(Performance, body.performance_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    if body.performance_date not in p.available_dates:
        raise _invalid("선택할 수 없는 관람일입니다.")
    if body.session_time not in p.slots:
        raise _invalid("선택할 수 없는 회차입니다.")

    # Price is always computed from the stored performance price, never taken from the client
    unit_price = p.price + (PREMIUM_SURCHARGE if body.seat_grade == "PREMIUM" else 0)
    order = Order(
        user_id=user.id,
        mbti=user.mbti,
        performance_id=p.id,
        performance_title=p.title,
        category=p.category,
        venue=p.venue,
        performance_date=body.performance_date,
        session_time=body.session_time,
        seat_grade=body.seat_grade,
        quantity=body.quantity,
        unit_price=unit_price,
        amount=unit_price * body.quantity,
        currency="KRW",
        payment_method=body.payment_method,
        status="MOCK_PAID",
        is_mock=True,
    )
    db.add(order)
    db.add(Event(user_id=user.id, mbti=user.mbti, type="mock_purchase",
                 performance_id=p.id, category=p.category))
    db.commit()
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(user: CurrentUser, db: DbSession):
    return db.scalars(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    ).all()
