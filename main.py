import os
import redis
import uuid
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI(title="Distributed Rate Limiter")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

pool = redis.ConnectionPool(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    decode_responses=True,
    max_connections=20
)

def get_redis():
    yield redis.Redis(connection_pool=pool)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LUA_FILENAME = "rate_limiter.lua" 
LUA_PATH = os.path.join(BASE_DIR, LUA_FILENAME)
with open(LUA_PATH, "r") as f:
    LUA_RATE_LIMITER_CODE = f.read()


@app.get("/health")
def health_check(r: redis.Redis = Depends(get_redis)):
    try:
        return {"status": "ok", "redis_connected": r.ping()}
    except redis.ConnectionError:
        return {"status": "error", "redis_connected": False}


@app.post("/add")
def add_value(key: str, value: str, r: redis.Redis = Depends(get_redis)):
    r.set(key, value)
    return {"message": f"Key '{key}' set successfully"}


@app.get("/get")
def get_value(key: str, r: redis.Redis = Depends(get_redis)):
    val = r.get(key)
    if val is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": val}


@app.get("/is_allowed")
def is_allowed(
    key: str, 
    limit: int = 5, 
    window: int = 60, 
    r: redis.Redis = Depends(get_redis)
):
    nonce = uuid.uuid4().hex[:6]
    
    try:
        script = r.register_script(LUA_RATE_LIMITER_CODE)
        allowed_flag, count = script(keys=[key], args=[limit, window, nonce])
        
        if not allowed_flag:
            raise HTTPException(
                status_code=429, 
                detail={
                    "message": "Rate limit exceeded",
                    "current_count": count,
                    "limit": limit
                }
            )
        
        return {
            "status": "allowed",
            "current_count": count,
            "limit": limit,
            "remaining": limit - count
        }

    except (redis.ConnectionError, redis.TimeoutError) as e:
        # implement proper logging
        print(f"CRITICAL: Redis connection failed. Failing open. Error: {e}")
        
        return {
            "status": "allowed",
            "message": "Rate limiting temporarily unavailable, failing open",
            "current_count": 0,
            "limit": limit,
            "remaining": limit
        }

@app.delete("/clear")
def clear_values(r: redis.Redis = Depends(get_redis)):
    r.flushdb()
    return {"message": "All keys cleared successfully"}