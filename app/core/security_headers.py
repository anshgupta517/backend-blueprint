from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """
    Adds security headers to every HTTP response.
    Pure ASGI middleware — same pattern as RequestLoggingMiddleware,
    no BaseHTTPMiddleware asyncio issues.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        # Prevent browsers from MIME-sniffing
                        # e.g. stops browser treating a text file as executable JS
                        (b"x-content-type-options", b"nosniff"),
                        # Clickjacking protection
                        # Prevents your app being embedded in an iframe on another site
                        (b"x-frame-options", b"DENY"),
                        # XSS protection for older browsers
                        (b"x-xss-protection", b"1; mode=block"),
                        # HTTPS enforcement — browser only connects via HTTPS
                        # max-age=31536000 = 1 year
                        # includeSubDomains = applies to all subdomains too
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        ),
                        # Controls what browser features the page can use
                        # Disable everything you don't need
                        (
                            b"permissions-policy",
                            b"geolocation=(), microphone=(), camera=()",
                        ),
                        # Content Security Policy
                        # Controls what resources the browser can load
                        # self = only from your own domain
                        # For API-only backends this is simple
                        (
                            b"content-security-policy",
                            b"default-src 'self'; frame-ancestors 'none'",
                        ),
                        # Don't send referrer info to other domains
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
