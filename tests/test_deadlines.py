from datetime import UTC, datetime, timedelta


def test_deadline_math_is_utc_and_positive():
    now = datetime.now(UTC)
    deadline = now + timedelta(minutes=15)
    assert deadline.tzinfo == UTC
    assert deadline > now
