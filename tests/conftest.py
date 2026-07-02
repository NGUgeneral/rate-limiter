import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from typing import AsyncGenerator, Generator
import main

@pytest.fixture
def mock_lua_runner() -> Generator[AsyncMock, None, None]:
    """Globally patches the LUA_SCRIPT_RUNNER as an AsyncMock for the duration of a test."""
    # FIX: Tell patch to explicitly construct an AsyncMock wrapper
    with patch("main.LUA_SCRIPT_RUNNER", new_callable=AsyncMock) as mocked:
        yield mocked

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an isolated HTTP client with Redis dependency bypassed using an explicit transport."""
    main.app.dependency_overrides[main.get_redis] = lambda: AsyncMock()
    
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    main.app.dependency_overrides.clear()