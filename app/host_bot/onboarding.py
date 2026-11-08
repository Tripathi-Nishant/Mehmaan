from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.host_bot.schemas import ListingFieldsUpdate


class OnboardingState(StrEnum):
    COLLECTING = "COLLECTING"
    READBACK = "READBACK"
    DONE = "DONE"
    ABANDONED = "ABANDONED"


REQUIRED_FIELDS = (
    "category",
    "activity_description",
    "duration_min",
    "max_guests",
    "price_per_person_paise",
    "city",
    "area",
    "available_weekdays",
    "start_time_local",
    "location_shared",
    "landmark",
    "consent_voice_clip",
    "cancellation_rule",
)


@dataclass
class OnboardingSession:
    fields: dict[str, Any] = field(default_factory=dict)
    state: OnboardingState = OnboardingState.COLLECTING
    turn_count: int = 0

    def merge(self, update: ListingFieldsUpdate) -> None:
        self.turn_count += 1
        self.fields.update(update.model_dump(exclude_none=True))
        if self.turn_count >= 12 and self.missing_fields:
            self.state = OnboardingState.ABANDONED
        elif not self.missing_fields:
            self.state = OnboardingState.READBACK

    @property
    def missing_fields(self) -> list[str]:
        missing = [name for name in REQUIRED_FIELDS if not self.fields.get(name)]
        if self.fields.get("category") == "food" and not self.fields.get("food_type"):
            missing.append("food_type")
        return missing

    def change(self, field_name: str) -> None:
        if field_name in self.fields:
            del self.fields[field_name]
        self.state = OnboardingState.COLLECTING

    def publish(self) -> None:
        if self.state != OnboardingState.READBACK:
            raise ValueError("listing cannot publish before read-back")
        self.state = OnboardingState.DONE
