from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from app.core.cache import cache


class FailingRedisClient:
    async def get(self, key):
        raise RuntimeError("redis unavailable")

    async def setex(self, key, ttl, value):
        raise RuntimeError("redis unavailable")

    async def delete(self, *keys):
        raise RuntimeError("redis unavailable")

    async def keys(self, pattern):
        raise RuntimeError("redis unavailable")


class TestCacheFailureResilience:
    async def test_get_user_succeeds_when_cache_get_fails(
        self,
        client: AsyncClient,
        test_user: dict,
        auth_headers: dict,
    ):
        with (
            patch.object(cache, "_client", FailingRedisClient()),
            patch.object(cache, "get", wraps=cache.get),
        ):
            response = await client.get(
                f"/api/v1/users/{test_user['id']}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    async def test_get_user_succeeds_when_cache_set_fails(
        self,
        client: AsyncClient,
        test_user: dict,
        auth_headers: dict,
    ):
        with (
            patch.object(cache, "_client", FailingRedisClient()),
            patch.object(cache, "set", wraps=cache.set),
        ):
            response = await client.get(
                f"/api/v1/users/{test_user['id']}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    async def test_update_user_succeeds_when_cache_invalidation_fails(
        self,
        client: AsyncClient,
        test_user: dict,
        auth_headers: dict,
    ):
        with (
            patch.object(cache, "_client", FailingRedisClient()),
            patch.object(cache, "delete", wraps=cache.delete),
            patch.object(cache, "delete_pattern", wraps=cache.delete_pattern),
        ):
            response = await client.patch(
                f"/api/v1/users/{test_user['id']}",
                json={"name": "Still Updates"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()["name"] == "Still Updates"
