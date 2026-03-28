from fastapi import Request

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
