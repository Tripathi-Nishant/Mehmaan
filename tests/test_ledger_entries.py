from app.payments.ledger import split_charge


def test_capture_ledger_entries_balance_to_zero():
    split = split_charge(250000, 1500)
    entries = [split.charge, -split.commission, -split.host_payable]
    assert sum(entries) == 0
