"""HTTP response hardening for the browser-facing application."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
    "img-src 'self' data:; connect-src 'self'; script-src 'self'; style-src 'self'"
)


def add_security_headers(app: FastAPI) -> None:
    """Apply safe default headers without breaking FastAPI's interactive docs assets."""

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers.setdefault("Content-Security-Policy", _CONTENT_SECURITY_POLICY)
        return response
