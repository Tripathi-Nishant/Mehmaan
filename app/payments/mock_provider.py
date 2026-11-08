import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class MockPayment:
    order_id: str
    payment_id: str
    signature: str


class MockProvider:
    def __init__(self, secret: str):
        self.secret = secret.encode()

    def create_order(self) -> str:
        return f"mock_order_{secrets.token_urlsafe(16)}"

    def pay(self, order_id: str) -> MockPayment:
        payment_id = f"mock_payment_{secrets.token_urlsafe(16)}"
        signature = hmac.new(
            self.secret, f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()
        return MockPayment(order_id, payment_id, signature)

    def verify(self, payment: MockPayment) -> bool:
        expected = hmac.new(
            self.secret, f"{payment.order_id}|{payment.payment_id}".encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, payment.signature)
