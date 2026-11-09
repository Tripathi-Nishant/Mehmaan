from dataclasses import dataclass


class LedgerBalanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class LedgerSplit:
    charge: int
    commission: int
    host_payable: int

    def validate(self) -> None:
        if self.charge != self.commission + self.host_payable:
            raise LedgerBalanceError("ledger does not balance")
        if min(self.charge, self.commission, self.host_payable) < 0:
            raise LedgerBalanceError("ledger amounts cannot be negative")


def refund_reversal(split: LedgerSplit, refund: int, host_keep: int) -> list[tuple[str, int]]:
    """Ledger rows that undo a capture: money back to the guest, commission and host share
    reversed, then the host's kept share (late cancel) re-booked. Capture + these sum to 0."""
    if refund + host_keep != split.charge or min(refund, host_keep) < 0:
        raise LedgerBalanceError("refund + host keep must equal the charge")
    entries = [
        ("REFUND", -refund),
        ("COMMISSION", split.commission),
        ("HOST_PAYABLE", split.host_payable),
    ]
    if host_keep:
        entries.append(("HOST_PAYABLE", -host_keep))
    return entries


def split_charge(amount_paise: int, commission_bps: int) -> LedgerSplit:
    commission = amount_paise * commission_bps // 10_000
    split = LedgerSplit(amount_paise, commission, amount_paise - commission)
    split.validate()
    return split
