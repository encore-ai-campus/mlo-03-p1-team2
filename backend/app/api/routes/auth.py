from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.core.security import create_access_token, hash_password
from app.models import User
from app.schemas.user import SignupIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

DUPLICATE = "이미 가입된 이메일입니다. 로그인해 주세요."


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: DbSession) -> TokenOut:
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        mbti=body.mbti,
        consent=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    return _token(user)
