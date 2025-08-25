import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_connection_manager, get_db
from backend.schemas import health as health_schemas
from backend.services.connection_manager import WebsocketsManager

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Health"]
)


@router.get("/health",
            response_model=health_schemas.HealthResponse,
            )
async def get_health():
    logger.debug("Health check")
    return health_schemas.HealthResponse(status="healthy")


@router.get("/health/db",
            response_model=health_schemas.DatabaseHealthResponse,
            )
async def get_db_health(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Check database health"""
    try:
        await db.execute(text("SELECT 1"))
        return health_schemas.DatabaseHealthResponse(
            status="healthy",
            error=None
        )
    except Exception as e:
        return health_schemas.DatabaseHealthResponse(
            status="unhealthy",
            error=str(e)
        )


@router.get("/health/redis",
            response_model=health_schemas.RedisHealthResponse,
            )
async def get_redis_health(
    connection_manager: Annotated[WebsocketsManager,
                                  Depends(get_connection_manager)]
):
    """Check Redis health"""
    try:
        await connection_manager.ping()
        return health_schemas.RedisHealthResponse(
            status="healthy",
            error=None
        )
    except Exception as e:
        return health_schemas.RedisHealthResponse(
            status="unhealthy",
            error=str(e)
        )
