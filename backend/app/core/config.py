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
PAYMENT_METHODS = ("간편결제", "신용카드", "계좌이체")
MBTI_TYPES = (
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
)
CATEGORIES = ("콘서트", "뮤지컬", "스포츠", "전시", "클래식", "연극")
