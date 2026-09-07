import uuid
from datetime import date

from pydantic import BaseModel, Field


class QueueRecipientRead(BaseModel):
    rank: int = Field(ge=1)
    recipient_site_id: uuid.UUID
    name: str
    priority: int = Field(ge=1, le=5)
    last_delivery_date: date | None
    days_since_last_delivery: int | None
    is_overdue: bool
    deliveries_last_30_days: int = Field(ge=0)
    pounds_last_30_days: float = Field(ge=0)
    total_deliveries: int = Field(ge=0)
    total_pounds: float = Field(ge=0)
    reason: str


class DeliveryQueueRead(BaseModel):
    as_of_date: date
    tie_window_days: int
    total: int = Field(ge=0)
    recipients: list[QueueRecipientRead]
