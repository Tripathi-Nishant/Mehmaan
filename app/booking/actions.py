from dataclasses import dataclass
from datetime import datetime

from app.booking.states import BookingStatus, transition
from app.payments.ledger import LedgerSplit, split_charge


@dataclass(frozen=True)
class PaymentCapture:
    status: BookingStatus
    ledger: LedgerSplit


class HoldExpiredError(RuntimeError):
    pass


def capture_payment(
    current: str,
    amount_paise: int,
    commission_bps: int,
    *,
    hold_expires_at: datetime | None,
    now: datetime,
) -> PaymentCapture:
    """HELD -> PAID_PENDING_HOST only while the hold is live (its seats may be released after)."""
    next_status = transition(BookingStatus(current), BookingStatus.PAID_PENDING_HOST)
    if hold_expires_at is not None and now >= hold_expires_at:
        raise HoldExpiredError("hold expired before payment")
    return PaymentCapture(next_status, split_charge(amount_paise, commission_bps))


def expire_hold(booking, slot) -> None:
    """HELD -> EXPIRED and give the seats back. Raises (seats untouched) if not HELD, so a
    booking already expired by the job is never released twice."""
    booking.status = transition(BookingStatus(booking.status), BookingStatus.EXPIRED).value
    if slot is not None:
        slot.booked_count = max(0, slot.booked_count - booking.guests)


def host_accept(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.CONFIRMED).value


def host_decline(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.DECLINED).value


def refund_declined(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.REFUNDED).value
