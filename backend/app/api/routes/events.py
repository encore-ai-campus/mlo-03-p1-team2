from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, OptionalUser
from app.models import Event, Performance
from app.schemas.event import EventIn, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def record_event(body: EventIn, user: OptionalUser, db: DbSession):
    p = db.get(Performance, body.performance_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    event = Event(
        user_id=user.id if user else None,
        mbti=user.mbti if user else None,
        type=body.type,
        performance_id=p.id,
        category=p.category,
    )
    db.add(event)
    db.commit()
    return event
