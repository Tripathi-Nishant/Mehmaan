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


def split_charge(amount_paise: int, commission_bps: int) -> LedgerSplit:
    commission = amount_paise * commission_bps // 10_000
    split = LedgerSplit(amount_paise, commission, amount_paise - commission)
    split.validate()
    return split
