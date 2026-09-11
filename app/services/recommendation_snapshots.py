import uuid
from collections.abc import Mapping
from decimal import Decimal
from typing import Final

from sqlalchemy.orm import Session

from app.models.recommendation_candidate import RecommendationCandidate
from app.models.recommendation_run import RecommendationRun
from app.schemas.donation_delivery_queue import DonationDeliveryQueueRead

RECOMMENDATION_POLICY_VERSION: Final = "v1"


def _as_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def save_recommendation_snapshot(
    db: Session,
    *,
    queue: DonationDeliveryQueueRead,
    offered_items_snapshot: list[Mapping[str, object]],
    policy_version: str = RECOMMENDATION_POLICY_VERSION,
) -> RecommendationRun:
    if not offered_items_snapshot:
        raise ValueError("offered_items_snapshot must not be empty")

    if queue.total != len(queue.recipients):
        raise ValueError("queue total must match recipient count")

    recommendation_run_id = uuid.uuid4()
    run = RecommendationRun(
        id=recommendation_run_id,
        donation_offer_id=queue.donation_offer_id,
        as_of_date=queue.as_of_date,
        policy_version=policy_version,
        tie_window_days=queue.tie_window_days,
        offered_total_pounds=_as_decimal(queue.total_offered_pounds),
        offered_items_snapshot=[dict(item) for item in offered_items_snapshot],
    )

    candidates = [
        RecommendationCandidate(
            id=uuid.uuid4(),
            recommendation_run_id=recommendation_run_id,
            recipient_site_id=recipient.recipient_site_id,
            rank=recipient.rank,
            recipient_name=recipient.name,
            priority=recipient.priority,
            last_delivery_date=recipient.last_delivery_date,
            days_since_last_delivery=recipient.days_since_last_delivery,
            is_overdue=recipient.is_overdue,
            deliveries_last_30_days=recipient.deliveries_last_30_days,
            pounds_last_30_days=_as_decimal(recipient.pounds_last_30_days),
            total_deliveries=recipient.total_deliveries,
            total_pounds=_as_decimal(recipient.total_pounds),
            reason=recipient.reason,
            matched_category_count=recipient.matched_category_count,
            known_potential_pounds=_as_decimal(recipient.known_potential_pounds),
            has_unknown_capacity=recipient.has_unknown_capacity,
            food_matches_snapshot=[
                match.model_dump(mode="json") for match in recipient.food_matches
            ],
        )
        for recipient in queue.recipients
    ]

    db.add(run)

    if candidates:
        db.add_all(candidates)

    db.flush()
    return run
