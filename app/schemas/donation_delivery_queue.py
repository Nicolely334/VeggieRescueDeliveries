import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.delivery_queue import QueueRecipientRead
from app.services.donation_matching import QuantityFit


class DonationQueueFoodMatchRead(BaseModel):
    food_category_code: str
    category_name: str
    offered_pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    maximum_pounds: float | None = Field(
        gt=0,
        allow_inf_nan=False,
    )
    potential_pounds: float | None = Field(
        gt=0,
        allow_inf_nan=False,
    )
    quantity_fit: QuantityFit


class DonationQueueRecipientRead(QueueRecipientRead):
    matched_category_count: int = Field(ge=1)
    known_potential_pounds: float = Field(
        ge=0,
        allow_inf_nan=False,
    )
    has_unknown_capacity: bool
    food_matches: list[DonationQueueFoodMatchRead] = Field(
        min_length=1,
    )


class DonationDeliveryQueueRead(BaseModel):
    donation_offer_id: uuid.UUID
    offer_status: Literal["open"]
    as_of_date: date
    tie_window_days: int = Field(ge=0)
    offered_category_count: int = Field(ge=1)
    total_offered_pounds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    total: int = Field(ge=0)
    recipients: list[DonationQueueRecipientRead]
