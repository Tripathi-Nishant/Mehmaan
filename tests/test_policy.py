from datetime import UTC, datetime, timedelta

import pytest

from app.booking.policy import NotCancellableError, cancellation_split

START = datetime(2026, 11, 20, 5, 30, tzinfo=UTC)


def at(hours_before: float) -> datetime:
    return START - timedelta(hours=hours_before)


def test_48h_or_more_is_full_refund():
    assert cancellation_split(300000, START, at(72)) == (300000, 0)


def test_exactly_48h_is_full_refund():
    assert cancellation_split(300000, START, at(48)) == (300000, 0)


def test_one_second_under_48h_host_keeps_20_percent():
    now = START - timedelta(hours=48) + timedelta(seconds=1)
    assert cancellation_split(300000, START, now) == (240000, 60000)


def test_odd_paise_go_to_the_guest():
    refund, keep = cancellation_split(300003, START, at(5))
    assert keep == 60000  # floor(60000.6)
    assert refund == 240003
    assert refund + keep == 300003


@pytest.mark.parametrize("now", [START, START + timedelta(minutes=1)])
def test_at_or_after_start_is_not_cancellable(now):
    with pytest.raises(NotCancellableError):
        cancellation_split(300000, START, now)
