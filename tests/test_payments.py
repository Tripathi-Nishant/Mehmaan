import pytest

from app.booking.service import Hold, SlotFullError
from app.payments.mock_provider import MockPayment, MockProvider


def test_mock_payment_signature_and_tamper_detection():
    provider = MockProvider("secret")
    payment = provider.pay(provider.create_order())
    assert provider.verify(payment)
    assert not provider.verify(MockPayment(payment.order_id, "tampered", payment.signature))


def test_hold_calculates_server_side_and_rejects_full_slot():
    hold = Hold(slot_capacity=2, booked_count=0, guests=2, price_per_person_paise=150000)
    hold.reserve()
    assert hold.amount_paise == 300000
    with pytest.raises(SlotFullError):
        Hold(2, 2, 1, 150000).reserve()
