import os
import redis
from fastapi import FastAPI

app = FastAPI(title="Distributed Rate Limiter")

# Setup Redis connection using environment variables for future AWS deployment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Initialize Redis with decode_responses=True so we get strings back, not bytes
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@app.get("/health")
def health_check():
    try:
        # Pinging Redis is a standard 'Engineering Guardrail' 
        is_connected = r.ping()
        return {"status": "ok", "redis_connected": is_connected}
    except redis.ConnectionError:
        return {"status": "error", "redis_connected": False}