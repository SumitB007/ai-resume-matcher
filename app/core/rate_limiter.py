"""Rate limiter — Redis-based sliding window rate limiting."""

from fastapi import HTTPException, status

from app.config import settings
from app.core.redis_client import redis_client


async def check_rate_limit(user_id: int, action: str = "match") -> None:
    """Check if a user has exceeded their rate limit.

    Uses a Redis sliding window counter: key = "ratelimit:{action}:{user_id}",
    expires after 60 seconds.

    Args:
        user_id: The authenticated user's ID.
        action: The action being rate-limited (default: "match").

    Raises:
        HTTPException 429: If the rate limit is exceeded.
    """
    key = f"ratelimit:{action}:{user_id}"

    try:
        current = await redis_client.get(key)

        if current is not None and int(current) >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {settings.rate_limit_per_minute} {action} requests per minute.",
            )

        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 60-second window
        await pipe.execute()

    except HTTPException:
        raise
    except Exception:
        # If Redis is down, allow the request (fail-open)
        pass
