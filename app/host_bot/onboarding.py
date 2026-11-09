from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.host_bot.schemas import ListingFieldsUpdate


class OnboardingState(StrEnum):
    COLLECTING = "COLLECTING"
    READBACK = "READBACK"
    DONE = "DONE"
    ABANDONED = "ABANDONED"


# Set by the Telegram location / voice / photo handlers, never by LLM extraction.
LOCATION_FIELDS = ("location_lat", "location_lng", "landmark_hi", "gate_photo_media_id")

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
    *LOCATION_FIELDS,
    "consent_voice_clip",
)


def location_complete(fields: dict[str, Any]) -> bool:
    return all(fields.get(name) not in (None, "") for name in LOCATION_FIELDS)


@dataclass
class OnboardingSession:
    fields: dict[str, Any] = field(default_factory=dict)
    state: OnboardingState = OnboardingState.COLLECTING
    turn_count: int = 0

    def merge(self, update: ListingFieldsUpdate) -> None:
        self.turn_count += 1
        self.fields.update(update.model_dump(exclude_none=True))
        self._advance()

    def set_field(self, name: str, value: Any) -> None:
        """Set a handler-owned field (pin, landmark, photo) without LLM extraction."""
        self.fields[name] = value
        self._advance()

    @property
    def next_field(self) -> str | None:
        return self.missing_fields[0] if self.missing_fields else None

    def _advance(self) -> None:
        if self.turn_count >= 12 and self.missing_fields:
            self.state = OnboardingState.ABANDONED
        elif not self.missing_fields:
            self.state = OnboardingState.READBACK

    @property
    def missing_fields(self) -> list[str]:
        # False is a valid answer (e.g. consent "nahi"); only absent/empty values are missing.
        missing = [name for name in REQUIRED_FIELDS if self.fields.get(name) in (None, "", [])]
        if self.fields.get("category") == "food" and not self.fields.get("food_type"):
            missing.append("food_type")
        return missing

    def change(self, field_name: str) -> None:
        self.fields.pop(field_name, None)
        self.state = OnboardingState.COLLECTING
        # A host fixing one field after a long onboarding must not hit the 12-turn abandon.
        self.turn_count = 0

    def publish(self) -> None:
        if self.state != OnboardingState.READBACK:
            raise ValueError("listing cannot publish before read-back")
        self.state = OnboardingState.DONE
