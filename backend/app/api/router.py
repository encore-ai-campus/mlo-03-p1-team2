from fastapi import APIRouter

from app.api.routes import auth

api_router = APIRouter(prefix="/api/v1")
for module in (auth,):
    api_router.include_router(module.router)
