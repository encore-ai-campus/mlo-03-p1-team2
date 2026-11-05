"""MongoDB 연결 (사용자 행동 이벤트 저장용). 첫 요청 때 한 번만 연결합니다."""
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.core.config import get_settings


@lru_cache
def _client() -> MongoClient:
    # 저장소가 내려가 있어도 요청이 오래 묶이지 않도록 시간 제한을 짧게 둡니다.
    return MongoClient(
        get_settings().mongodb_url, tz_aware=True,
        serverSelectionTimeoutMS=2000, connectTimeoutMS=2000, socketTimeoutMS=5000,
    )


_indexes_ready = False


def _ensure_indexes(col: Collection) -> None:
    """분석 쿼리에 자주 쓰는 인덱스. 실패해도 저장은 계속합니다 (다음 요청에서 다시 시도)."""
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        col.create_index([("type", ASCENDING), ("occurred_at", DESCENDING)])
        col.create_index([("user_id", ASCENDING), ("occurred_at", DESCENDING)])
        col.create_index([("session_id", ASCENDING), ("occurred_at", ASCENDING)])
        _indexes_ready = True
    except PyMongoError:
        pass


def get_event_collection() -> Collection:
    """FastAPI 의존성. 테스트에서는 가짜 컬렉션으로 바꿔 끼웁니다."""
    s = get_settings()
    col = _client()[s.mongodb_db][s.mongodb_events_collection]
    _ensure_indexes(col)
    return col
