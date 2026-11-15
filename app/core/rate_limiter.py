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


async def check_rate_limit_key(key: str, limit: int, window_seconds: int, what: str) -> None:
    """Generic fixed-window limiter over an arbitrary Redis key (Phase 8).

    Same fail-open-on-Redis-error policy as check_rate_limit: availability
    of the API beats strictness of the limit when Redis itself is down.
    """
    if limit <= 0:
        return
    try:
        current = await redis_client.get(key)
        if current is not None and int(current) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {what}. Please slow down and try again later.",
            )
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        await pipe.execute()
    except HTTPException:
        raise
    except Exception:
        pass


def client_ip(request) -> str:
    """Best-effort client IP: first X-Forwarded-For hop, else the peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_ip_rate_limit(request, action: str, per_minute: int, daily_cap: int | None = None) -> None:
    """Per-IP limits for unauthenticated surfaces (auth, anonymous checker)."""
    ip = client_ip(request)
    await check_rate_limit_key(f"ratelimit:{action}:ip:{ip}", per_minute, 60, action)
    if daily_cap:
        from datetime import date

        await check_rate_limit_key(
            f"ratelimit:{action}:ipday:{ip}:{date.today().isoformat()}",
            daily_cap,
            86400,
            action,
        )


async def check_daily_ai_cap(user_id: int) -> None:
    """Per-user daily cap across AI generation endpoints (Phase 8 cost control)."""
    from datetime import date

    await check_rate_limit_key(
        f"ratelimit:ai-daily:{user_id}:{date.today().isoformat()}",
        settings.ai_daily_cap,
        86400,
        "AI generation (daily cap)",
    )
