# routers/__init__.py
from fastapi import APIRouter
from routers.recommend_router import recommend_router
from routers.auth_router import auth_router

api_router = APIRouter()

# Include auth endpoints
api_router.include_router(auth_router)

# Include recommend endpoints
api_router.include_router(recommend_router)
