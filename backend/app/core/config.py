from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://tikit:tikit@localhost:3306/tikit?charset=utf8mb4"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]


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
