from fastapi import APIRouter

from app.api.routes import auth, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users):
    api_router.include_router(module.router)
