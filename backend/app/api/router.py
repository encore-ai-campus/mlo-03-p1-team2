from fastapi import APIRouter

from app.api.routes import admin, auth, events, favorites, mypage, orders, performances, reservations, tracking, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users, mypage, performances, orders, reservations, favorites, events, tracking, admin):
    api_router.include_router(module.router)
