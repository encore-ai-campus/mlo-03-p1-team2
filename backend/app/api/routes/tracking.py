from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError, PyMongoError

from app.core.security import decode_access_token
from app.db.mongo import get_event_collection
from app.schemas.tracking import TrackingBatchIn, TrackingBatchOut

router = APIRouter(prefix="/tracking", tags=["tracking"])
_bearer = HTTPBearer(auto_error=False)
DUPLICATE_KEY = 11000


def _user_id(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str | None:
    # 토큰이 만료·위조돼도 이벤트를 버리지 않고 비회원 이벤트로 저장합니다.
    # 사용자 id 는 클라이언트가 보낸 값이 아니라 서명이 검증된 토큰에서만 가져옵니다.
    return decode_access_token(creds.credentials) if creds else None


@router.post("/events", response_model=TrackingBatchOut, status_code=status.HTTP_202_ACCEPTED)
def collect_events(
    body: TrackingBatchIn,
    events: Annotated[Collection, Depends(get_event_collection)],
    user_id: Annotated[str | None, Depends(_user_id)],
    user_agent: Annotated[str | None, Header()] = None,
):
    received_at = datetime.now(timezone.utc)
    docs = []
    for e in body.events:
        doc = e.model_dump(mode="python")
        event_id = str(e.event_id)
        doc.update(
            _id=event_id,  # 같은 이벤트를 다시 보내면(재시도) 중복 저장되지 않습니다.
            event_id=event_id,
            session_id=str(e.session_id),
            anonymous_id=str(e.anonymous_id),
            user_id=user_id,
            user_agent=(user_agent or "")[:300],
            received_at=received_at,
        )
        docs.append(doc)

    try:
        events.insert_many(docs, ordered=False)
    except BulkWriteError as exc:
        errors = exc.details.get("writeErrors", [])
        if any(err.get("code") != DUPLICATE_KEY for err in errors):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "이벤트를 저장하지 못했습니다.") from exc
        return TrackingBatchOut(accepted=len(docs) - len(errors), duplicates=len(errors))
    except PyMongoError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "이벤트 저장소에 연결할 수 없습니다.") from exc
    return TrackingBatchOut(accepted=len(docs), duplicates=0)
