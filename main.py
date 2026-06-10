import os
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status
)
from redis import asyncio as aioredis
from mangum import Mangum

from config import settings
from schemas import RateCheckRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pool = None
LUA_SCRIPT_RUNNER = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, LUA_SCRIPT_RUNNER

    pool = aioredis.ConnectionPool.from_url(
        url=settings.redis_url,
        decode_responses=True,
        max_connections=5
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    lua_path = os.path.join(base_dir, "rate_limiter.lua")
    with open(lua_path, "r") as f:
        lua_code = f.read()
        
    _init_client = aioredis.Redis(connection_pool=pool)
    LUA_SCRIPT_RUNNER = _init_client.register_script(lua_code)
    
    yield  # Control handed over to FastAPI to process requests
    
    # Clean up and close the pool sockets gracefully at shutdown
    if pool:
        await pool.disconnect()


app = FastAPI(title="Distributed Rate Limiter", lifespan=lifespan)


async def get_redis():
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection pool is uninitialized."
        )
    return aioredis.Redis(connection_pool=pool)


@app.get("/health")
async def health_check(r: aioredis.Redis = Depends(get_redis)):
    try:
        redis_alive = await r.ping()
        return {"status": "ok", "redis_connected": redis_alive}
    except Exception:
        return {"status": "error", "redis_connected": False}


@app.post("/v1/is_allowed", status_code=status.HTTP_200_OK)
async def is_allowed(
    payload: RateCheckRequest, 
    r: aioredis.Redis = Depends(get_redis)
):
    nonce = uuid.uuid4().hex[:6]
    if payload.client_key:
        # Token based request flow
        redis_key = f"{{ratelimiter}}:v1:token:{payload.client_key}"
        if payload.max_requests is None or payload.window_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token-authenticated requests must explicitly supply limit and window metrics."
            )
        active_limit = payload.max_requests
        active_window = payload.window_seconds
    else:
        # IP based request flow
        redis_key = f"{{ratelimiter}}:v1:ip:{payload.ip_key}"
        active_limit = payload.max_requests if payload.max_requests else settings.default_ip_limit
        active_window = payload.window_seconds if payload.window_seconds else settings.default_ip_window
    
    try:
        allowed_flag, count = await LUA_SCRIPT_RUNNER(
            keys=[redis_key], 
            args=[active_limit, active_window, nonce],
            client=r
        )
        
        if not allowed_flag:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                detail={
                    "message": "Rate limit exceeded",
                    "current_count": count,
                    "limit": active_limit
                }
            )
        
        return {
            "status": "allowed",
            "current_count": count,
            "limit": active_limit,
            "remaining": max(0, active_limit - count)
        }

    except Exception as e:
        logger.error(f"CRITICAL: Redis connection failed. Failing open. Error: {e}")
        return {
            "status": "allowed",
            "message": "Rate limiting temporarily unavailable, failing open",
            "current_count": 0,
            "limit": active_limit,
            "remaining": active_limit
        }

handler = Mangum(app)