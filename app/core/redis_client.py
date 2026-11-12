"""Redis client — shared connection for caching, rate limiting, and task status."""

import redis.asyncio as redis

from app.config import settings

# ── Async Redis Client ──
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    """Dependency that returns the shared Redis client."""
    return redis_client
