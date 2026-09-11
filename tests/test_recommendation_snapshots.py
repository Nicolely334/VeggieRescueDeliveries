import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from sqlalchemy.orm import Session

from app.schemas.donation_delivery_queue import (
    DonationDeliveryQueueRead,
    DonationQueueFoodMatchRead,
    DonationQueueRecipientRead,
)
from app.services.recommendation_snapshots import (
    save_recommendation_snapshot,
)


def test_save_recommendation_snapshot_builds_run_and_candidates() -> None:
    offer_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    queue = DonationDeliveryQueueRead(
        donation_offer_id=offer_id,
        offer_status="open",
        as_of_date=date(2026, 9, 11),
        tie_window_days=3,
        offered_category_count=1,
        total_offered_pounds=100.0,
        total=1,
        recipients=[
            DonationQueueRecipientRead(
                rank=1,
                recipient_site_id=recipient_id,
                name="Community Food Pantry",
                priority=1,
                last_delivery_date=None,
                days_since_last_delivery=None,
                is_overdue=True,
                deliveries_last_30_days=0,
                pounds_last_30_days=0.0,
                total_deliveries=0,
                total_pounds=0.0,
                reason="No completed delivery history",
                matched_category_count=1,
                known_potential_pounds=75.0,
                has_unknown_capacity=False,
                food_matches=[
                    DonationQueueFoodMatchRead(
                        food_category_code="produce",
                        category_name="Produce",
                        offered_pounds=100.0,
                        maximum_pounds=75.0,
                        potential_pounds=75.0,
                        quantity_fit="partial_offer_fits",
                    )
                ],
            )
        ],
    )
    db = Mock(spec=Session)

    run = save_recommendation_snapshot(
        db,
        queue=queue,
        offered_items_snapshot=[
            {
                "food_category_code": "produce",
                "category_name": "Produce",
                "pounds": 100.0,
            }
        ],
    )

    assert run.donation_offer_id == offer_id
    assert run.offered_total_pounds == Decimal("100.0")
    assert run.offered_items_snapshot[0]["food_category_code"] == "produce"
    db.add.assert_called_once_with(run)

    candidates = db.add_all.call_args.args[0]
    assert len(candidates) == 1

    candidate = candidates[0]
    assert candidate.recommendation_run_id == run.id
    assert candidate.recipient_site_id == recipient_id
    assert candidate.rank == 1
    assert candidate.known_potential_pounds == Decimal("75.0")
    assert candidate.food_matches_snapshot[0]["quantity_fit"] == "partial_offer_fits"
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
