import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()
SERVICE_NAME = "red-team-arena-api"
logger = logging.getLogger(__name__)


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@router.get("/database", response_model=None)
async def database_health(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str] | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        logger.exception("Database health check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "postgresql"},
        )

    return {"status": "ok", "service": "postgresql"}
