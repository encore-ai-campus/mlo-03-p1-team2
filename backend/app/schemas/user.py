from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.config import MBTI_TYPES

Mbti = Literal[MBTI_TYPES]  # type: ignore[valid-type]


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str
    mbti: Mbti
    consent: bool

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("consent")
    @classmethod
    def require_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("개인정보 수집에 동의해 주세요.")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupIn":
        if self.password != self.password_confirm:
            raise ValueError("비밀번호가 일치하지 않습니다.")
        return self


class ProfileUpdateIn(BaseModel):
    """Partial update of the logged-in user's profile. Omitted fields are left unchanged."""

    name: str | None = Field(None, min_length=1, max_length=30)
    email: EmailStr | None = None
    mbti: Mbti | None = None
    # Required only when changing the email (re-authentication for a sensitive change)
    current_password: str | None = Field(None, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return v.strip().lower() if v is not None else v


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeIn":
        if self.new_password != self.new_password_confirm:
            raise ValueError("새 비밀번호가 일치하지 않습니다.")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    mbti: str
    consent: bool
    consented_at: datetime
    created_at: datetime
    is_admin: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
