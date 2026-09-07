import uuid
from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class FoodCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    is_active: bool
    created_at: datetime


class RecipientFoodPreferenceInput(BaseModel):
    food_category_code: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9_]+$",
    )
    maximum_pounds: float | None = Field(
        default=None,
        gt=0,
        allow_inf_nan=False,
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
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


class RecipientFoodPreferencesReplace(BaseModel):
    items: list[RecipientFoodPreferenceInput]

    @model_validator(mode="after")
    def validate_unique_categories(self) -> Self:
        category_codes = [item.food_category_code for item in self.items]

        if len(category_codes) != len(set(category_codes)):
            raise ValueError("food categories cannot be repeated")

        return self


class RecipientFoodPreferenceRead(BaseModel):
    id: uuid.UUID
    food_category_code: str
    category_name: str
    maximum_pounds: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RecipientFoodPreferencesRead(BaseModel):
    recipient_site_id: uuid.UUID
    recipient_name: str
    preferences: list[RecipientFoodPreferenceRead]
