"""Health check endpoints for monitoring."""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check with service status."""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check MinIO
    try:
        from app.services.storage_service import storage_service
        # Simple check - list buckets
        storage_service.client.list_buckets()
        health_status["services"]["storage"] = "healthy"
    except Exception as e:
        health_status["services"]["storage"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status