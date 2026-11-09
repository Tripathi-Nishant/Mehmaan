from datetime import datetime, timedelta

FULL_REFUND_BEFORE = timedelta(hours=48)
LATE_HOST_KEEP_PERCENT = 20


class NotCancellableError(ValueError):
    pass


def cancellation_split(amount_paise: int, starts_at: datetime, now: datetime) -> tuple[int, int]:
    """Fixed policy -> (refund to guest, kept by host). >=48h before start: full refund.
    Later: host keeps floor(20%), so any odd paisa goes back to the guest."""
    if now >= starts_at:
        raise NotCancellableError("the experience has already started")
    if starts_at - now >= FULL_REFUND_BEFORE:
        return amount_paise, 0
    keep = amount_paise * LATE_HOST_KEEP_PERCENT // 100
    return amount_paise - keep, keep
