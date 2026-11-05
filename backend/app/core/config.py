from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://tikit:tikit@localhost:3306/tikit?charset=utf8mb4"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    # 사용자 행동 로그(MongoDB). 인증이 필요한 서버면 mongodb://user:pw@host:27017/?authSource=admin 형식
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "tikit"
    mongodb_events_collection: str = "events"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Booking rules mirrored from sample/dist/app.js
PREMIUM_SURCHARGE = 30000
MAX_QUANTITY = 4
# 프리미엄 추가금과 최대 수량을 포함해도 예매·결제의 INT 금액 범위를 넘지 않게 합니다.
MAX_PERFORMANCE_PRICE = 2_147_483_647 // MAX_QUANTITY - PREMIUM_SURCHARGE
PAYMENT_METHODS = ("간편결제", "신용카드", "계좌이체")
MBTI_TYPES = (
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
)
CATEGORIES = ("콘서트", "뮤지컬", "스포츠", "전시", "클래식", "연극")

# 예매(reservations) 흐름의 상태값
RESERVATION_STATUSES = ("REQUESTED", "CONFIRMED", "CANCELLED")
PAYMENT_STATUSES = ("PENDING", "COMPLETED", "CANCELLED")
# 인기순·랭킹의 "구매 수"로 집계하는 이벤트: 기존 즉시 모의 결제(orders) + 예매 결제 완료
PURCHASE_EVENT_TYPES = ("mock_purchase", "payment_completed")

# 프론트엔드가 MongoDB 로 보내는 사용자 행동 이벤트(type). frontend/src/utils/tracker.js 의 EVENT_TYPES 와 같게 유지합니다.
TRACKING_EVENT_TYPES = (
    # 탐색
    "page_view",                   # 화면 이동
    "search",                      # 검색어 제출
    "category_select",             # 카테고리 선택 (목록 칩, 취향 모달)
    "sort_change",                 # 정렬 변경
    "list_expand",                 # 공연 목록 더보기/접기
    "performance_view",            # 공연 상세(예매 모달) 열기
    "taste_view",                  # MBTI 취향 모달·리포트 보기
    # 찜
    "favorite_add",
    "favorite_remove",
    # 예매·결제
    "booking_start",               # 날짜·회차 선택 후 예매하기
    "reservation_request",         # 예매 요청 성공
    "payment_complete",            # 모의 결제 완료
    "reservation_cancel",          # 예매 취소
    # 계정
    "sign_up",
    "login",
    "logout",
    "profile_update",
    "password_change",
    "notification_settings_update",
    "account_withdraw",
)
TRACKING_MAX_BATCH = 10  # 프론트엔드 큐 최대 크기와 같음
