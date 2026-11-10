from datetime import UTC, datetime
from types import SimpleNamespace

from app.web.booking_routes import templates


def render(refund, keep, amount=300000):
    return templates.get_template("cancel.html").render(
        booking=SimpleNamespace(access_token="tok", guests=2, amount_paise=amount),
        slot=SimpleNamespace(starts_at=datetime(2026, 11, 14, 5, 30, tzinfo=UTC)),
        listing=SimpleNamespace(title_en="Dal baati with Meena"),
        host=SimpleNamespace(display_name="Meena"),
        refund=refund,
        keep=keep,
    )


def test_late_cancel_states_refund_and_host_share():
    html = render(240000, 60000)
    assert "You will receive ₹2,400 back. Meena ji keeps ₹600." in html
    assert "less than 48 hours" in html
    assert 'action="/b/tok/cancel"' in html and 'href="/b/tok"' in html


def test_early_cancel_is_a_full_refund():
    html = render(300000, 0)
    assert "You will receive the full ₹3,000 back." in html
    assert "Meena ji keeps" not in html


def test_odd_paise_are_shown():
    assert "₹2,400.03" in render(240003, 60000, amount=300003)
