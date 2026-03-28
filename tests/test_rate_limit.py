from fastapi import Request
from httpx import AsyncClient

from app.core.rate_limit import RateLimit, limiter


class TestRateLimitDependency:
    async def test_dependency_uses_current_slowapi_signature(self, monkeypatch):
        dependency = RateLimit("5/minute")
        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/v1/auth/login",
                "raw_path": b"/api/v1/auth/login",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            }
        )
        captured = {}

        def fake_check_request_limit(request_arg, endpoint_func, in_middleware=True):
            captured["request"] = request_arg
            captured["endpoint_func"] = endpoint_func
            captured["in_middleware"] = in_middleware

        monkeypatch.setattr(limiter, "_check_request_limit", fake_check_request_limit)

        await dependency(request)

        assert captured["request"] is request
        assert captured["endpoint_func"] is dependency._endpoint
        assert captured["in_middleware"] is False


class TestLoginRateLimit:
    async def test_successful_login_is_allowed_before_threshold(
        self,
        isolated_rate_limited_client: AsyncClient,
    ):
        create_response = await isolated_rate_limited_client.post(
            "/api/v1/users",
            json={
                "name": "Rate Limited User",
                "email": "ratelimit@example.com",
                "password": "testpassword123",
            },
        )
        assert create_response.status_code == 201

        response = await isolated_rate_limited_client.post(
            "/api/v1/auth/login",
            json={
                "email": "ratelimit@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_failed_login_attempts_are_rate_limited(
        self,
        isolated_rate_limited_client: AsyncClient,
    ):
        statuses = []
        for _ in range(6):
            response = await isolated_rate_limited_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nobody@test.com",
                    "password": "wrongpassword",
                },
            )
            statuses.append(response.status_code)

        assert statuses[:5] == [401, 401, 401, 401, 401]
        assert statuses[5] == 429
