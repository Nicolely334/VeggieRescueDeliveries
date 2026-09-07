import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class FarmBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    address: str | None = Field(
        default=None,
        max_length=300,
    )
    city: str | None = Field(
        default=None,
        max_length=100,
    )
    region: str | None = Field(
        default=None,
        max_length=100,
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        allow_inf_nan=False,
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        allow_inf_nan=False,
    )
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned_name = value.strip()

        if not cleaned_name:
            raise ValueError("name cannot be blank")

        return cleaned_name

    @field_validator(
        "address",
        "city",
        "region",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class FarmCreate(FarmBase):
    pass


class FarmRead(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
