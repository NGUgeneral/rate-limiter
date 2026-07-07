import pytest
import httpx
from httpx import AsyncClient
from unittest.mock import AsyncMock
from collections.abc import AsyncGenerator
import main

@pytest.fixture
async def mock_lua_runner():
    """Creates a mock instance for the global Lua script execution boundary."""
    return AsyncMock()

@pytest.fixture
async def client(mock_lua_runner) -> AsyncGenerator[AsyncClient, None]:
    """Provides an isolated HTTP client with the global Redis Lua runner mocked out."""
    main.LUA_SCRIPT_RUNNER = mock_lua_runner
    main.pool = AsyncMock()

    async with AsyncClient(
        transport=httpx.ASGITransport(app=main.app), 
        base_url="http://test"
    ) as ac:
        yield ac

    main.LUA_SCRIPT_RUNNER = None
    main.pool = None