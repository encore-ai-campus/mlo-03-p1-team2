from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import PasswordChangeIn, ProfileUpdateIn, UserOut

router = APIRouter(prefix="/users", tags=["users"])

WRONG_PASSWORD = "현재 비밀번호가 일치하지 않습니다."


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdateIn, user: CurrentUser, db: DbSession):
    if body.email is not None and body.email != user.email:
        # Changing the login email is sensitive, so the current password is required
        if not body.current_password or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(status.HTTP_403_FORBIDDEN, WRONG_PASSWORD)
        if db.scalar(select(User.id).where(User.email == body.email, User.id != user.id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 이메일입니다.")
        user.email = body.email
    if body.name is not None:
        user.name = body.name
    if body.mbti is not None:
        user.mbti = body.mbti
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 이메일입니다.")
    db.refresh(user)
    return user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChangeIn, user: CurrentUser, db: DbSession) -> Response:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, WRONG_PASSWORD)
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "현재 비밀번호와 다른 비밀번호를 입력해 주세요.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
