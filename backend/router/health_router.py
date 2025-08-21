import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from backend.services.connection_manager import WebsocketsManager
from backend.core.dependencies import get_connection_manager, get_db
from backend.schemas import health as health_schemas


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health",
            response_model=health_schemas.HealthResponse,
            tags=["Health"]
            )
async def health():
    logger.debug("Health check")
    return health_schemas.HealthResponse(status="healthy")


@router.get("/health/db",
            response_model=health_schemas.DatabaseHealthResponse,
            tags=["Health"])
async def db_health(
    db: AsyncSession = Depends(get_db)
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
            tags=["Health"]
            )
async def redis_health(
    connection_manager: WebsocketsManager = Depends(get_connection_manager)
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
