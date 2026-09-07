import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeliveryItemRead(BaseModel):
    category_code: str
    category_name: str
    pounds: float = Field(ge=0)


class DeliveryRead(BaseModel):
    id: uuid.UUID
    recipient_site_id: uuid.UUID
    delivery_date: date
    recipient: str
    location: str
    produce_pounds: float | None
    packaged_pounds: float | None
    driver: str
    vehicle: str
    total_pounds: float = Field(ge=0)
    items: list[DeliveryItemRead]
    source_recipient_name: str | None
    created_at: datetime
    status: Literal["completed"]


class DeliveryListRead(BaseModel):
    total: int = Field(ge=0)
    deliveries: list[DeliveryRead]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
