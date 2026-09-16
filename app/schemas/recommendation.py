import uuid

from pydantic import BaseModel

from app.schemas.donation_delivery_queue import DonationDeliveryQueueRead


class RecommendationSnapshotCreated(BaseModel):
    recommendation_run_id: uuid.UUID
    policy_version: str
    queue: DonationDeliveryQueueRead