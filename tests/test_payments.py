from app.payments.mock_provider import MockPayment, MockProvider


def test_mock_payment_signature_and_tamper_detection():
    provider = MockProvider("secret")
    payment = provider.pay(provider.create_order())
    assert provider.verify(payment)
    assert not provider.verify(MockPayment(payment.order_id, "tampered", payment.signature))
