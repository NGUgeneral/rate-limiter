import os
import redis
import uuid
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status
)
from mangum import Mangum

from config import settings
from schemas import RateCheckRequest

app = FastAPI(title="Distributed Rate Limiter")

pool = redis.ConnectionPool.from_url(
    url=settings.redis_url,
    decode_responses=True,
    max_connections=5
)

def get_redis():
    return redis.Redis(connection_pool=pool)

# Load the atomic sliding-window engine at boot
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LUA_FILENAME = "rate_limiter.lua" 
LUA_PATH = os.path.join(BASE_DIR, LUA_FILENAME)
with open(LUA_PATH, "r") as f:
    LUA_RATE_LIMITER_CODE = f.read()

_init_client = redis.Redis(connection_pool=pool)
LUA_SCRIPT_RUNNER = _init_client.register_script(LUA_RATE_LIMITER_CODE)


@app.get("/health")
def health_check(r: redis.Redis = Depends(get_redis)):
    try:
        return {"status": "ok", "redis_connected": r.ping()}
    except redis.ConnectionError:
        return {"status": "error", "redis_connected": False}


@app.post("/v1/is_allowed", status_code=status.HTTP_200_OK)
def is_allowed(
    payload: RateCheckRequest, 
    r: redis.Redis = Depends(get_redis)
):
    nonce = uuid.uuid4().hex[:6]
    if payload.client_key:
        # Token based request flow;
        redis_key = f"{{ratelimiter}}:v1:token:{payload.client_key}"
        if payload.max_requests is None or payload.window_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token-authenticated requests must explicitly supply limit and window metrics."
            )
        active_limit = payload.max_requests
        active_window = payload.window_seconds
    else:
        # IP based request flow;
        redis_key = f"{{ratelimiter}}:v1:ip:{payload.ip_key}"
        active_limit = payload.max_requests if payload.max_requests else settings.default_ip_limit
        active_window = payload.window_seconds if payload.window_seconds else settings.default_ip_window
    
    try:
        allowed_flag, count = LUA_SCRIPT_RUNNER(
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

    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"CRITICAL: Redis connection failed. Failing open. Error: {e}")
        return {
            "status": "allowed",
            "message": "Rate limiting temporarily unavailable, failing open",
            "current_count": 0,
            "limit": active_limit,
            "remaining": active_limit
        }

handler = Mangum(app)