from dataclasses import dataclass


class SlotFullError(RuntimeError):
    pass


@dataclass
class Hold:
    slot_capacity: int
    booked_count: int
    guests: int
    price_per_person_paise: int

    @property
    def amount_paise(self) -> int:
        return self.guests * self.price_per_person_paise

    def reserve(self) -> None:
        if self.guests < 1 or self.booked_count + self.guests > self.slot_capacity:
            raise SlotFullError("slot does not have enough capacity")
        self.booked_count += self.guests
