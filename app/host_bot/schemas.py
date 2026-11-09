from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ListingFieldsUpdate(BaseModel):
    category: str | None = None
    activity_description: str | None = Field(default=None, min_length=3)
    duration_min: int | None = Field(default=None, ge=30, le=720)
    max_guests: int | None = Field(default=None, ge=1, le=50)
    price_per_person_paise: int | None = Field(default=None, ge=1)
    city: str | None = None
    area: str | None = None
    available_weekdays: list[int] | None = None
    start_time_local: str | None = None
    food_type: str | None = None
    consent_voice_clip: bool | None = None

    @field_validator("start_time_local")
    @classmethod
    def start_time_is_hh_mm(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")
        except ValueError as exc:
            raise ValueError('start_time_local must be 24-hour "HH:MM", e.g. "17:00"') from exc

    @field_validator("available_weekdays")
    @classmethod
    def weekdays_are_valid(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and any(day not in range(7) for day in value):
            raise ValueError("weekdays must use numbers 0 through 6")
        return value


class IntentResult(BaseModel):
    intent: Literal["YES", "NO", "CHANGE", "PAYOUT_QUERY", "NEW_LISTING", "UNCLEAR"]
    field: str | None = None
