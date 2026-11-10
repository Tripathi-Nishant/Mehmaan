from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.web.ratelimit import RateLimiter


class PublicRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 20):
        super().__init__(app)
        self.limiter = RateLimiter(limit=limit)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(("/book", "/pay/", "/interpreter/", "/media/")) or path.endswith(
            "/translate"
        ):
            client = request.client.host if request.client else "unknown"
            if not self.limiter.allow(client):
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        return await call_next(request)
