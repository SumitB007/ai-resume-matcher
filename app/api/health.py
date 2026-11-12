"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health Check")
async def health_check():
    """Returns service health status including Redis connectivity."""
    # Check Redis connectivity
    redis_status = "unknown"
    cache_stats = {}
    try:
        from app.core.redis_client import redis_client

        pong = await redis_client.ping()
        redis_status = "connected" if pong else "error"

        from app.services.cache_service import get_cache_stats

        cache_stats = await get_cache_stats()
    except Exception as e:
        redis_status = f"error: {e}"

    # Check Celery broker connectivity
    celery_status = "unknown"
    try:
        from app.tasks.celery_app import celery_app

        conn = celery_app.connection()
        conn.connect()
        conn.release()
        celery_status = "connected"
    except Exception as e:
        celery_status = f"error: {e}"

    return {
        "status": "healthy",
        "service": "AI Resume & Job Matcher",
        "version": "0.1.0",
        "redis": redis_status,
        "cache": cache_stats,
        "celery": celery_status,
    }

