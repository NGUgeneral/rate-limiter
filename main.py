import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from redis import asyncio as aioredis

from config import settings
from schemas import RateCheckRequest
from services.ratelimit import execute_rate_check
from grpc_server.server import GRPCServerManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pool = None
LUA_SCRIPT_RUNNER = None
grpc_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, LUA_SCRIPT_RUNNER, grpc_manager

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

    grpc_manager = GRPCServerManager(pool=pool, lua_runner=LUA_SCRIPT_RUNNER, port=50051)
    await grpc_manager.start()
    
    yield

    if grpc_manager:
        await grpc_manager.stop(grace=5)
    
    if pool:
        await pool.disconnect()


app = FastAPI(title="Distributed Rate Limiter", lifespan=lifespan)

@app.post("/api/v1/is_allowed")
async def check_rate_http(payload: RateCheckRequest, response: Response):
    res = await execute_rate_check(
        pool=pool,
        lua_runner=LUA_SCRIPT_RUNNER,
        access_key=payload.access_key,
        ip_key=payload.ip_key,
        limit=payload.limit,
        window=payload.window
    )

    if "validation_error" in res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client must explicitly supply limit and window metrics when utilizing token layout."
        )

    if not res["allowed"]:
        response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        return {
            "status": "blocked",
            "detail": {
                "message": res["message"],
                "current_count": res["current_count"],
                "limit": res["limit"]
            }
        }

    return {
        "status": "allowed",
        "current_count": res["current_count"],
        "limit": res["limit"],
        "remaining": res["remaining"],
        "message": res["message"]
    }