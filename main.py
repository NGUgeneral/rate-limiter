import os
import redis
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query
)

app = FastAPI(title="Distributed Rate Limiter")

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Connection Pool (Established once at startup)
pool = redis.ConnectionPool(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    decode_responses=True,
    max_connections=20
)

def get_redis():
    """Dependency that provides a redis client from the pool."""
    yield redis.Redis(connection_pool=pool)

@app.get("/health")
def health_check(r: redis.Redis = Depends(get_redis)):
    try:
        return {"status": "ok", "redis_connected": r.ping()}
    except redis.ConnectionError:
        return {"status": "error", "redis_connected": False}

@app.post("/add")
def add_value(
    key: str, 
    value: str, 
    r: redis.Redis = Depends(get_redis)
):
    # Set the key in Redis
    r.set(key, value)
    return {"message": f"Key '{key}' set successfully"}

@app.get("/get")
def get_value(
    key: str, 
    r: redis.Redis = Depends(get_redis)
):
    val = r.get(key)
    if val is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": val}

@app.delete("/clear")
def clear_values(r: redis.Redis = Depends(get_redis)):
    r.flushdb()
    return {"message": "All keys cleared successfully"}