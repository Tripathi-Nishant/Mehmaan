from app.web.ratelimit import RateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip")
    assert limiter.allow("ip")
    assert not limiter.allow("ip")
