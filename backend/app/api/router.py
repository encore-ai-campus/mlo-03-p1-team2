from fastapi import APIRouter

from app.api.routes import auth, events, favorites, mypage, orders, performances, reservations, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users, mypage, performances, orders, reservations, favorites, events):
    api_router.include_router(module.router)
