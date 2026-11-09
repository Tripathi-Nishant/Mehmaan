from app.web.ratelimit import RateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip")
    assert limiter.allow("ip")
    assert not limiter.allow("ip")


def test_book_route_is_rate_limited():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.web.guards import PublicRateLimitMiddleware

    app = FastAPI()
    app.add_middleware(PublicRateLimitMiddleware, limit=1)
    app.post("/book")(lambda: {"ok": True})
    client = TestClient(app)
    assert client.post("/book").status_code == 200
    assert client.post("/book").status_code == 429
