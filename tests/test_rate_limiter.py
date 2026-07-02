import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio

class TestRateLimiter:

    # --- TOKEN STRATEGY TESTS ---

    async def test_token_strategy_success(self, client: AsyncClient, mock_lua_runner: AsyncMock):
        """GIVEN an access_key with explicit limits, THEN utilize token layout."""
        mock_lua_runner.return_value = (1, 2)
        payload = {
            "access_key": "test_token_123",
            "ip_key": "127.0.0.1",
            "limit": 100,
            "window": 60
        }

        response = await client.post("/api/v1/is_allowed", json=payload)
        
        assert response.status_code == 200
        assert response.json()["status"] == "allowed"
        assert response.json()["remaining"] == 98
        
        called_kwargs = mock_lua_runner.call_args[1]
        assert called_kwargs["keys"] == ["{ratelimiter}:v1:token:test_token_123"]

    async def test_token_strategy_missing_metrics_raises_400(self, client: AsyncClient):
        """GIVEN an access_key without metrics, THEN raise 400."""
        payload = {
            "access_key": "test_token_123",
            "ip_key": "127.0.0.1"
        }

        response = await client.post("/api/v1/is_allowed", json=payload)
        
        assert response.status_code == 400
        assert "must explicitly supply limit and window metrics" in response.json()["detail"]


    # --- IP STRATEGY TESTS ---

    async def test_ip_strategy_fallback_success(self, client: AsyncClient, mock_lua_runner: AsyncMock):
        """GIVEN no access_key, THEN fallback to IP address layout."""
        mock_lua_runner.return_value = (1, 1)
        payload = {
            "ip_key": "192.168.1.50"
        }

        response = await client.post("/api/v1/is_allowed", json=payload)

        assert response.status_code == 200
        called_kwargs = mock_lua_runner.call_args[1]
        assert called_kwargs["keys"] == ["{ratelimiter}:v1:ip:192.168.1.50"]


    # --- EDGE CASES ---

    async def test_rate_limit_exceeded_raises_429(self, client: AsyncClient, mock_lua_runner: AsyncMock):
        """GIVEN a budget infraction, THEN return 429."""
        mock_lua_runner.return_value = (0, 10)
        payload = {
            "ip_key": "127.0.0.1", 
            "limit": 10, 
            "window": 60
        }

        response = await client.post("/api/v1/is_allowed", json=payload)

        assert response.status_code == 429
        assert response.json()["detail"]["message"] == "Rate limit exceeded"

    async def test_redis_exception_triggers_fail_open(self, client: AsyncClient, mock_lua_runner: AsyncMock):
        """GIVEN Redis failure, THEN fail-open gracefully."""
        mock_lua_runner.side_effect = Exception("Redis crash")
        payload = {
            "access_key": "resilient_key", 
            "ip_key": "127.0.0.1",
            "limit": 10, 
            "window": 60
        }

        response = await client.post("/api/v1/is_allowed", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "allowed"
        assert "failing open" in response.json()["message"]