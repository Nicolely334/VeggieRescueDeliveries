import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

DonationAllocationStatus = Literal[
    "planned",
    "assigned",
    "completed",
    "cancelled",
]


class DonationAllocationItemCreate(BaseModel):
    food_category_code: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )
    pounds: float = Field(
        gt=0,
        multiple_of=0.01,
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


class DonationAllocationCreate(BaseModel):
    recommendation_run_id: uuid.UUID
    recipient_site_id: uuid.UUID
    is_override: bool = False
    override_reason: str | None = Field(
        default=None,
        max_length=2000,
    )
    driver_name: str | None = Field(
        default=None,
        max_length=200,
    )
    vehicle_name: str | None = Field(
        default=None,
        max_length=200,
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )
    items: list[DonationAllocationItemCreate] = Field(
        min_length=1,
    )

    @field_validator(
        "override_reason",
        "driver_name",
        "vehicle_name",
        "notes",
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

    @model_validator(mode="after")
    def validate_allocation(self) -> Self:
        category_codes = [item.food_category_code for item in self.items]

        if len(category_codes) != len(set(category_codes)):
            raise ValueError("food categories cannot be repeated")

        if self.is_override and self.override_reason is None:
            raise ValueError("override_reason is required when is_override is true")

        if not self.is_override and self.override_reason is not None:
            raise ValueError("override_reason requires is_override to be true")

        return self


class DonationAllocationItemRead(BaseModel):
    id: uuid.UUID
    food_category_code: str
    category_name: str
    pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    created_at: datetime


class DonationAllocationRead(BaseModel):
    id: uuid.UUID
    donation_offer_id: uuid.UUID
    recommendation_run_id: uuid.UUID
    recipient_site_id: uuid.UUID
    recipient_name: str
    status: DonationAllocationStatus
    is_override: bool
    override_reason: str | None
    driver_name: str | None
    vehicle_name: str | None
    notes: str | None
    total_pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    items: list[DonationAllocationItemRead] = Field(
        min_length=1,
    )
    created_at: datetime
    updated_at: datetime


class DonationAllocationListRead(BaseModel):
    donation_offer_id: uuid.UUID
    total: int = Field(ge=0)
    total_allocated_pounds: float = Field(
        ge=0,
        allow_inf_nan=False,
    )
    allocations: list[DonationAllocationRead]
