import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

DonationOfferStatus = Literal[
    "open",
    "allocated",
    "completed",
    "cancelled",
]


class DonationOfferItemCreate(BaseModel):
    food_category_code: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )
    pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )

    @field_validator(
        "food_category_code",
        mode="before",
    )
    @classmethod
    def normalize_category_code(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            return value.strip().casefold()

        return value


class DonationOfferCreate(BaseModel):
    farm_id: uuid.UUID
    available_from: datetime | None = None
    pickup_by: datetime | None = None
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )
    items: list[DonationOfferItemCreate] = Field(
        min_length=1,
    )

    @field_validator("notes")
    @classmethod
    def clean_notes(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None

    @model_validator(mode="after")
    def validate_offer(self) -> Self:
        for field_name, value in (
            ("available_from", self.available_from),
            ("pickup_by", self.pickup_by),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{field_name} must include a timezone")

        if (
            self.available_from is not None
            and self.pickup_by is not None
            and self.pickup_by < self.available_from
        ):
            raise ValueError("pickup_by cannot be earlier than available_from")

        category_codes = [item.food_category_code for item in self.items]

        if len(category_codes) != len(set(category_codes)):
            raise ValueError("food categories cannot be repeated")

        return self


class DonationOfferItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    food_category_code: str
    category_name: str
    pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    created_at: datetime


class DonationOfferRead(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    farm_name: str
    status: DonationOfferStatus
    available_from: datetime | None
    pickup_by: datetime | None
    notes: str | None
    total_pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    items: list[DonationOfferItemRead]
    created_at: datetime
    updated_at: datetime


class DonationOfferListRead(BaseModel):
    total: int = Field(ge=0)
    offers: list[DonationOfferRead]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
