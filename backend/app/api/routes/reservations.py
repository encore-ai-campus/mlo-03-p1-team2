"""예매 → 모의 결제 → 취소 API (booking-app에서 옮겨 온 기능)

- POST /reservations                 예매 요청 + 결제 대기 생성
- GET  /reservations                 내 예매 목록 (결제 정보 포함)
- GET  /payments                     내 결제 목록
- POST /reservations/{id}/complete   모의 결제 완료 → 예매 확정
- POST /reservations/{id}/cancel     예매·결제 동시 취소

예매·결제 생성/변경, 상태 이력, 이벤트 기록은 하나의 트랜잭션으로 저장합니다.
"""
import logging
import random
import time
from collections.abc import Callable
from typing import Literal, TypeVar

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.core.config import PREMIUM_SURCHARGE
from app.models import Event, Payment, Performance, Reservation, StatusHistory, User
from app.models.user import utcnow
from app.schemas.reservation import PaymentOut, ReservationIn, ReservationOut

router = APIRouter(tags=["reservations"])
log = logging.getLogger(__name__)
T = TypeVar("T")

NOT_FOUND = "예매 내역을 찾을 수 없습니다."
KEY_REUSED = "이미 사용한 예매 요청 키입니다. 예매 창을 다시 열어 주세요."
# 같은 요청 키로 다시 보냈을 때 비교하는 항목
_SAME_REQUEST_FIELDS = ("performance_id", "performance_date", "session_time", "seat_grade", "quantity")
# MariaDB/MySQL이 "트랜잭션을 다시 실행하라"고 돌려주는 오류: 1213 데드락, 1205 잠금 대기 시간 초과
RETRYABLE_DB_ERRORS = {1213, 1205}
MAX_ATTEMPTS = 3


def _is_retryable(exc: OperationalError) -> bool:
    args = getattr(exc.orig, "args", ())
    return bool(args) and args[0] in RETRYABLE_DB_ERRORS


def _with_retry(db: Session, work: Callable[[], T]) -> T:
    """트랜잭션 전체(work)를 실행하고, 데드락·잠금 대기 시간 초과면 롤백 후 처음부터 다시 실행합니다.

    롤백하면 세션의 객체가 만료되므로 work는 매번 DB에서 상태를 다시 읽습니다.
    work가 변경 없이 끝나거나(이미 같은 상태, 같은 요청 재전송) HTTPException으로 끝나도
    트랜잭션을 여기서 닫습니다. 그래야 FOR UPDATE 잠금이 응답 전에 풀리고, 트랜잭션 종료 시점의
    데드락도 재시도 범위 안에서 처리됩니다(응답 후 get_db의 close에서 터지지 않습니다).
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = work()
            if db.in_transaction():
                db.commit()   # 변경이 없으면 잠금만 풉니다. expire_on_commit=False라 객체는 그대로입니다.
            return result
        except HTTPException:
            db.rollback()
            raise
        except OperationalError as exc:
            db.rollback()
            if not _is_retryable(exc) or attempt == MAX_ATTEMPTS:
                raise
            log.warning("retrying transaction after MariaDB error %s (attempt %d/%d)",
                        exc.orig.args[0], attempt, MAX_ATTEMPTS)
            # 경합한 트랜잭션끼리 같은 순간에 다시 부딪히지 않도록 조금씩 다르게 기다립니다.
            time.sleep(random.uniform(0.01, 0.05) * attempt)
    raise AssertionError("unreachable")


def _history(db: Session, r: Reservation, entity: str, before: str | None, after: str, at) -> None:
    db.add(StatusHistory(reservation_id=r.id, user_id=r.user_id, entity=entity,
                         from_status=before, to_status=after, created_at=at))


def _event(db: Session, user: User, r: Reservation, kind: str, at) -> None:
    # 수집에 동의한 사용자만 분석용 이벤트를 남깁니다.
    if user.consent:
        db.add(Event(user_id=user.id, mbti=user.mbti, type=kind, performance_id=r.performance_id,
                     category=r.category, reservation_id=r.id, created_at=at))


def _find_by_key(db: Session, user_id: str, key: str) -> Reservation | None:
    return db.scalar(select(Reservation).where(Reservation.user_id == user_id, Reservation.request_key == key))


def _replay(existing: Reservation, body: ReservationIn, response: Response) -> Reservation:
    """같은 요청 키의 재시도: 내용이 같으면 기존 예매(200), 다르면 409"""
    if any(getattr(existing, f) != getattr(body, f) for f in _SAME_REQUEST_FIELDS):
        raise HTTPException(status.HTTP_409_CONFLICT, KEY_REUSED)
    response.status_code = status.HTTP_200_OK
    return existing


@router.post("/reservations", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(body: ReservationIn, response: Response, user: CurrentUser, db: DbSession):
    p = db.get(Performance, body.performance_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    if body.performance_date not in p.available_dates:
        raise HTTPException(422, "선택할 수 없는 관람일입니다.")
    if body.session_time not in p.slots:
        raise HTTPException(422, "선택할 수 없는 회차입니다.")

    key = str(body.request_key)
    return _with_retry(db, lambda: _create_once(db, p, body, response, user, key))


def _create_once(db: Session, p: Performance, body: ReservationIn, response: Response, user: User, key: str):
    existing = _find_by_key(db, user.id, key)
    if existing:
        return _replay(existing, body, response)

    # 가격은 항상 서버에 저장된 공연 가격으로 계산합니다.
    unit_price = p.price + (PREMIUM_SURCHARGE if body.seat_grade == "PREMIUM" else 0)
    amount = unit_price * body.quantity
    now = utcnow()
    r = Reservation(
        user_id=user.id, mbti=user.mbti, performance_id=p.id, performance_title=p.title,
        category=p.category, venue=p.venue, performance_date=body.performance_date,
        session_time=body.session_time, seat_grade=body.seat_grade, quantity=body.quantity,
        unit_price=unit_price, amount=amount, status="REQUESTED", request_key=key,
        created_at=now, updated_at=now,
    )
    r.payment = Payment(amount=amount, currency="KRW", status="PENDING", requested_at=now, updated_at=now)
    db.add(r)
    try:
        # 고유 키 위반은 INSERT가 실행되는 flush에서 나므로 flush부터 commit까지 함께 감쌉니다.
        db.flush()  # id 확정 (이력·이벤트에서 참조)
        _history(db, r, "reservation", None, "REQUESTED", now)
        _history(db, r, "payment", None, "PENDING", now)
        _event(db, user, r, "reservation_requested", now)
        db.commit()
    except IntegrityError:
        # 같은 키로 동시에 들어온 요청: 먼저 저장된 예매를 돌려줍니다.
        db.rollback()
        existing = _find_by_key(db, user.id, key)
        if existing is None:
            raise
        return _replay(existing, body, response)
    return r


@router.get("/reservations", response_model=list[ReservationOut])
def list_reservations(user: CurrentUser, db: DbSession):
    return db.scalars(
        select(Reservation).where(Reservation.user_id == user.id)
        .order_by(Reservation.created_at.desc(), Reservation.id)
    ).unique().all()


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(user: CurrentUser, db: DbSession):
    rows = db.scalars(
        select(Reservation).where(Reservation.user_id == user.id)
        .order_by(Reservation.created_at.desc(), Reservation.id)
    ).unique().all()
    return [
        PaymentOut(
            id=r.payment.id, reservation_id=r.id, performance_id=r.performance_id,
            performance_title=r.performance_title, performance_date=r.performance_date,
            session_time=r.session_time, quantity=r.quantity, amount=r.payment.amount,
            currency=r.payment.currency, status=r.payment.status, requested_at=r.payment.requested_at,
            completed_at=r.payment.completed_at, cancelled_at=r.payment.cancelled_at,
        )
        for r in rows
    ]


@router.post("/reservations/{reservation_id}/{action}", response_model=ReservationOut)
def change_reservation(reservation_id: str, action: Literal["complete", "cancel"], user: CurrentUser, db: DbSession):
    return _with_retry(db, lambda: _change_once(db, reservation_id, action, user))


def _change_once(db: Session, reservation_id: str, action: str, user: User):
    # 행 잠금(FOR UPDATE)으로 결제·취소가 동시에 들어와도 상태가 한 번만 바뀌게 합니다.
    r = db.scalar(
        select(Reservation).where(Reservation.id == reservation_id, Reservation.user_id == user.id)
        .with_for_update(of=Reservation)
    )
    if r is None:  # 없는 예매와 다른 사용자의 예매를 구분하지 않습니다.
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)

    new_r, new_p = ("CONFIRMED", "COMPLETED") if action == "complete" else ("CANCELLED", "CANCELLED")
    if r.status == new_r:  # 같은 작업의 재시도는 그대로 돌려줍니다(이력 중복 없음).
        return r
    if action == "complete" and r.status == "CANCELLED":
        raise HTTPException(status.HTTP_409_CONFLICT, "취소한 예매는 결제할 수 없습니다.")

    now = utcnow()
    old_r, old_p = r.status, r.payment.status
    r.status, r.updated_at = new_r, now
    r.payment.status, r.payment.updated_at = new_p, now
    if action == "complete":
        r.payment.completed_at = now
    else:
        r.cancelled_at = now
        r.payment.cancelled_at = now  # 결제 완료 시각과 금액은 그대로 보존
    _history(db, r, "reservation", old_r, new_r, now)
    _history(db, r, "payment", old_p, new_p, now)
    _event(db, user, r, "payment_completed" if action == "complete" else "reservation_cancelled", now)
    db.commit()
    return r
