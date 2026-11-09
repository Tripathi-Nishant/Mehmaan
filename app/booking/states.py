from enum import StrEnum


class BookingStatus(StrEnum):
    HELD = "HELD"
    PAID_PENDING_HOST = "PAID_PENDING_HOST"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"  # by the traveler; refund per booking/policy.py


ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.HELD: {BookingStatus.PAID_PENDING_HOST, BookingStatus.EXPIRED},
    BookingStatus.PAID_PENDING_HOST: {
        BookingStatus.CONFIRMED,
        BookingStatus.DECLINED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.DECLINED: {BookingStatus.REFUNDED},
    BookingStatus.CONFIRMED: {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.COMPLETED: set(),
    BookingStatus.REFUNDED: set(),
    BookingStatus.EXPIRED: set(),
    BookingStatus.CANCELLED: set(),
}


class InvalidTransitionError(RuntimeError):
    pass


def transition(current: BookingStatus, target: BookingStatus) -> BookingStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"invalid booking transition {current} -> {target}")
    return target
