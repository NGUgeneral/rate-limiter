import logging
import grpc

from stubs.python.ratelimit.v1 import ratelimit_pb2
from stubs.python.ratelimit.v1 import ratelimit_pb2_grpc

from services.ratelimit import execute_rate_check

logger = logging.getLogger(__name__)

class RateLimitergRPCService(ratelimit_pb2_grpc.RateLimiterServiceServicer):
    def __init__(self, pool, lua_runner):
        self.pool = pool
        self.lua_runner = lua_runner

    async def IsAllowed(
        self, 
        request: ratelimit_pb2.IsAllowedRequest, 
        context: grpc.aio.ServicerContext
    ) -> ratelimit_pb2.IsAllowedResponse:
        
        access_key = request.access_key if request.HasField("access_key") else None
        limit = request.limit if request.HasField("limit") else None
        window = request.window if request.HasField("window") else None
        
        res = await execute_rate_check(
            pool=self.pool,
            lua_runner=self.lua_runner,
            access_key=access_key,
            ip_key=request.ip_key,
            limit=limit,
            window=window
        )
        
        return ratelimit_pb2.IsAllowedResponse(
            status=res["status"],
            current_count=res["current_count"],
            limit=res["limit"],
            remaining=res["remaining"],
            message=res["message"]
        )

class GRPCServerManager:
    def __init__(self, pool, lua_runner, port: int = 50051):
        self.pool = pool
        self.lua_runner = lua_runner
        self.port = port
        self.server = None

    async def start(self):
        self.server = grpc.aio.server()
        ratelimit_pb2_grpc.add_RateLimiterServiceServicer_to_server(
            RateLimitergRPCService(self.pool, self.lua_runner), self.server
        )
        listen_addr = f"[::]:{self.port}"
        self.server.add_insecure_port(listen_addr)
        logger.info(f"gRPC Server boot sequence complete. Listening on {listen_addr}")
        await self.server.start()

    async def stop(self, grace: int = 5):
        if self.server:
            logger.info("Stopping gRPC server instance gracefully...")
            await self.server.stop(grace=grace)