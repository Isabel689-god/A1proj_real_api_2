from fastapi import APIRouter
from app.api.v1 import chat
from app.api.v1 import dashboard
from app.api.v1 import knowledge
from app.api.v1 import monitor
from app.api.v1 import user

api_router = APIRouter()

api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(knowledge.router)
api_router.include_router(monitor.router)
api_router.include_router(user.router)
