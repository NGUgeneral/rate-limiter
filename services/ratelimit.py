import uuid
import logging
from redis import asyncio as aioredis
from config import settings

logger = logging.getLogger(__name__)

async def execute_rate_check(
        pool: aioredis.ConnectionPool,
        lua_runner,
        access_key: str | None,
        ip_key: str,
        limit: int | None,
        window: int | None
    ) -> dict:
    nonce = str(uuid.uuid4())
    r = aioredis.Redis(connection_pool=pool)

    if access_key:
        if limit is None or window is None:
            return {
                "allowed": False,
                "validation_error": "Token strategy requires explicit limit and window metrics.",
                "current_count": 0,
                "limit": 0,
                "remaining": 0,
                "message": "Token strategy requires explicit limit and window metrics."
            }
        redis_key = f"{{ratelimiter}}:v1:token:{access_key}"
        active_limit = limit
        active_window = window
    else:
        redis_key = f"{{ratelimiter}}:v1:ip:{ip_key}"
        active_limit = limit if limit is not None else settings.default_ip_limit
        active_window = window if window is not None else settings.default_ip_window
        
    try:
        allowed_flag, count = await lua_runner(
            keys=[redis_key], 
            args=[active_limit, active_window, nonce],
            client=r
        )
        
        if not allowed_flag:
            return {
                "allowed": False,
                "current_count": count,
                "limit": active_limit,
                "remaining": 0,
                "message": "Rate limit exceeded"
            }
            
        return {
            "allowed": True,
            "current_count": count,
            "limit": active_limit,
            "remaining": max(0, active_limit - count),
            "message": None
        }
    except Exception as e:
        logger.error(f"CRITICAL: Redis execution anomaly. Defaulting FAIL-OPEN. Error: {e}")
        return {
            "allowed": True,
            "current_count": 0,
            "limit": active_limit,
            "remaining": active_limit,
            "message": f"Rate limiting temporarily unavailable, failing open. Error: {e}"
        }