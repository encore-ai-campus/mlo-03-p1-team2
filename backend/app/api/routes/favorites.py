from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Favorite, Performance

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[str])
def list_favorites(user: CurrentUser, db: DbSession):
    return db.scalars(
        select(Favorite.performance_id)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at)
    ).all()


@router.put("/{performance_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(performance_id: str, user: CurrentUser, db: DbSession) -> Response:
    if not db.get(Performance, performance_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공연을 찾을 수 없습니다.")
    if not db.get(Favorite, (user.id, performance_id)):
        db.add(Favorite(user_id=user.id, performance_id=performance_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{performance_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(performance_id: str, user: CurrentUser, db: DbSession) -> Response:
    fav = db.get(Favorite, (user.id, performance_id))
    if fav:
        db.delete(fav)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
