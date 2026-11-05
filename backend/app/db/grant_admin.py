"""기존 회원에게 관리자 권한 부여: python -m app.db.grant_admin <이메일>"""
import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def grant_admin(db: Session, email: str) -> bool:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise ValueError("가입된 회원을 찾을 수 없습니다. 먼저 웹에서 회원가입해 주세요.")
    if user.is_admin:
        return False
    user.is_admin = True
    db.commit()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="가입된 회원에게 공연 관리 권한을 부여합니다.")
    parser.add_argument("email", help="기존 회원의 로그인 이메일")
    args = parser.parse_args()

    from app.db.session import SessionLocal

    with SessionLocal() as session:
        try:
            changed = grant_admin(session, args.email)
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        print("관리자 권한을 부여했습니다. 다시 로그인해 주세요." if changed else "이미 관리자 계정입니다.")
