from dataclasses import dataclass

from app.booking.states import BookingStatus, transition
from app.payments.ledger import LedgerSplit, split_charge


@dataclass(frozen=True)
class PaymentCapture:
    status: BookingStatus
    ledger: LedgerSplit


def capture_payment(current: str, amount_paise: int, commission_bps: int) -> PaymentCapture:
    next_status = transition(BookingStatus(current), BookingStatus.PAID_PENDING_HOST)
    return PaymentCapture(next_status, split_charge(amount_paise, commission_bps))


def host_accept(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.CONFIRMED).value


def host_decline(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.DECLINED).value


def refund_declined(current: str) -> str:
    return transition(BookingStatus(current), BookingStatus.REFUNDED).value
