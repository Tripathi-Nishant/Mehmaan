from pydantic import BaseModel, Field

from app.host_bot.schemas import ListingFieldsUpdate


class ExtractionResult(ListingFieldsUpdate):
    pass


class ListingCopy(BaseModel):
    title_en: str = Field(min_length=5, max_length=120)
    description_en: str = Field(min_length=20, max_length=800)
    landmark_en: str | None = Field(default=None, max_length=200)
