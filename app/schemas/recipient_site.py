import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipientSiteBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    priority: int = Field(ge=1, le=5)
    is_active: bool = True
    is_fallback: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned_name = value.strip()

        if not cleaned_name:
            raise ValueError("name cannot be blank")

        return cleaned_name


class RecipientSiteCreate(RecipientSiteBase):
    pass


class RecipientSiteRead(RecipientSiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
