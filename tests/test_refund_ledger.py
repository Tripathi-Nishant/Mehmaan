import pytest

from app.payments.ledger import LedgerBalanceError, refund_reversal, split_charge

SPLIT = split_charge(300000, 1500)  # charge 3000, commission 450, host 2550 (rupees)
CAPTURE = [("CHARGE", 300000), ("COMMISSION", -45000), ("HOST_PAYABLE", -255000)]


def test_full_refund_reverses_everything():
    entries = refund_reversal(SPLIT, refund=300000, host_keep=0)
    assert entries == [("REFUND", -300000), ("COMMISSION", 45000), ("HOST_PAYABLE", 255000)]
    assert sum(a for _, a in CAPTURE + entries) == 0


def test_late_cancel_host_keeps_share_and_ledger_balances():
    entries = refund_reversal(SPLIT, refund=240000, host_keep=60000)
    assert ("HOST_PAYABLE", -60000) in entries
    assert sum(a for _, a in CAPTURE + entries) == 0


def test_refund_plus_keep_must_equal_charge():
    with pytest.raises(LedgerBalanceError):
        refund_reversal(SPLIT, refund=240000, host_keep=0)
