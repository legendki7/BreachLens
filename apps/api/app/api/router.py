from fastapi import APIRouter

from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.duels import router as duels_router
from app.api.routes.guardrails import router as guardrails_router
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.api.routes.red_agent import router as red_agent_router

api_router = APIRouter()
api_router.include_router(duels_router, prefix="/duels", tags=["duels"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(guardrails_router, prefix="/guardrails", tags=["guardrails"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(red_agent_router, prefix="/red-agent", tags=["red-agent"])
