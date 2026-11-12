"""Cache service — Redis-based caching for match results and other expensive operations.

Provides get/set/invalidate operations for match results, keyed by
resume_id + job_id. Cache TTL is configurable (default: 1 hour).
"""

import json
import logging
from datetime import datetime

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour)
MATCH_CACHE_TTL = 3600


def _match_cache_key(resume_id: int, job_id: int) -> str:
    """Generate a Redis key for a match result."""
    return f"match_cache:{resume_id}:{job_id}"


def _user_matches_key(user_id: int) -> str:
    """Generate a Redis key for tracking a user's cached match keys."""
    return f"user_matches:{user_id}"


async def get_cached_match(resume_id: int, job_id: int) -> dict | None:
    """Retrieve a cached match result from Redis.

    Args:
        resume_id: The resume ID.
        job_id: The job description ID.

    Returns:
        Cached match result dict, or None if not found/expired.
    """
    key = _match_cache_key(resume_id, job_id)
    try:
        cached = await redis_client.get(key)
        if cached:
            logger.info(f"✅ Cache HIT for match {resume_id}↔{job_id}")
            data = json.loads(cached)
            # Restore datetime from ISO string
            if "created_at" in data and isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            return data
        logger.info(f"❌ Cache MISS for match {resume_id}↔{job_id}")
        return None
    except Exception as e:
        logger.warning(f"Redis cache get failed: {e}")
        return None


async def set_cached_match(
    resume_id: int,
    job_id: int,
    user_id: int,
    match_data: dict,
    ttl: int = MATCH_CACHE_TTL,
) -> None:
    """Store a match result in Redis cache.

    Args:
        resume_id: The resume ID.
        job_id: The job description ID.
        user_id: The user who owns this match.
        match_data: The match result dict to cache.
        ttl: Time-to-live in seconds (default: 1 hour).
    """
    key = _match_cache_key(resume_id, job_id)
    try:
        # Serialize datetime objects to ISO format for JSON
        serializable = _make_serializable(match_data)
        await redis_client.setex(key, ttl, json.dumps(serializable))

        # Track this key under the user's match set (for bulk invalidation)
        user_key = _user_matches_key(user_id)
        await redis_client.sadd(user_key, key)
        await redis_client.expire(user_key, ttl)

        logger.info(f"Cached match {resume_id}↔{job_id} (TTL={ttl}s)")
    except Exception as e:
        logger.warning(f"Redis cache set failed: {e}")


async def invalidate_match(resume_id: int, job_id: int) -> None:
    """Invalidate a specific cached match result.

    Called when a resume or job is updated and the old match is stale.

    Args:
        resume_id: The resume ID.
        job_id: The job description ID.
    """
    key = _match_cache_key(resume_id, job_id)
    try:
        await redis_client.delete(key)
        logger.info(f"Invalidated cache for match {resume_id}↔{job_id}")
    except Exception as e:
        logger.warning(f"Redis cache invalidate failed: {e}")


async def invalidate_user_matches(user_id: int) -> None:
    """Invalidate all cached match results for a user.

    Called when a user updates their resume, which affects all matches.

    Args:
        user_id: The user's ID.
    """
    user_key = _user_matches_key(user_id)
    try:
        match_keys = await redis_client.smembers(user_key)
        if match_keys:
            await redis_client.delete(*match_keys, user_key)
            logger.info(f"Invalidated {len(match_keys)} cached matches for user {user_id}")
    except Exception as e:
        logger.warning(f"Redis bulk invalidate failed: {e}")


async def get_cache_stats() -> dict:
    """Get cache statistics for monitoring.

    Returns:
        Dict with cache stats (total keys, memory usage).
    """
    try:
        info = await redis_client.info("memory")
        dbsize = await redis_client.dbsize()
        return {
            "total_keys": dbsize,
            "memory_used": info.get("used_memory_human", "unknown"),
            "memory_peak": info.get("used_memory_peak_human", "unknown"),
        }
    except Exception as e:
        logger.warning(f"Redis stats failed: {e}")
        return {"error": str(e)}


def _make_serializable(data: dict) -> dict:
    """Convert a dict to JSON-serializable form (handle datetime objects)."""
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _make_serializable(value)
        else:
            result[key] = value
    return result
