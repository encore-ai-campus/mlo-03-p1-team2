from fastapi import APIRouter

from app.api.routes import auth, events, favorites, orders, performances, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users, performances, orders, favorites, events):
    api_router.include_router(module.router)
