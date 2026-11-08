from app.booking.service import Hold, SlotFullError


def test_last_seat_can_only_be_reserved_once():
    slot = Hold(slot_capacity=1, booked_count=0, guests=1, price_per_person_paise=10000)
    slot.reserve()
    second_attempt = Hold(
        slot_capacity=slot.slot_capacity,
        booked_count=slot.booked_count,
        guests=1,
        price_per_person_paise=10000,
    )
    try:
        second_attempt.reserve()
    except SlotFullError:
        pass
    else:
        raise AssertionError("second reservation unexpectedly succeeded")
