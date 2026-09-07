import uuid
from datetime import date
from decimal import Decimal

import app.models  # noqa: F401
from app.db.base import Base
from app.models.recommendation_candidate import (
    RecommendationCandidate,
)
from app.models.recommendation_run import RecommendationRun


def test_recommendation_tables_are_registered() -> None:
    assert "recommendation_runs" in Base.metadata.tables
    assert "recommendation_candidates" in Base.metadata.tables


def test_recommendation_run_preserves_offer_snapshot() -> None:
    offer_id = uuid.uuid4()

    run = RecommendationRun(
        donation_offer_id=offer_id,
        as_of_date=date(2026, 9, 7),
        policy_version="v1",
        tie_window_days=3,
        offered_total_pounds=Decimal("100.00"),
        offered_items_snapshot=[
            {
                "food_category_code": "produce",
                "category_name": "Produce",
                "pounds": 100.0,
            }
        ],
    )

    assert run.donation_offer_id == offer_id
    assert run.offered_total_pounds == Decimal("100.00")
    assert run.offered_items_snapshot[0]["food_category_code"] == "produce"


def test_candidate_preserves_ranking_snapshot() -> None:
    candidate = RecommendationCandidate(
        recommendation_run_id=uuid.uuid4(),
        recipient_site_id=uuid.uuid4(),
        rank=1,
        recipient_name="Community Food Pantry",
        priority=1,
        last_delivery_date=None,
        days_since_last_delivery=None,
        is_overdue=True,
        deliveries_last_30_days=0,
        pounds_last_30_days=Decimal("0.00"),
        total_deliveries=0,
        total_pounds=Decimal("0.00"),
        reason="No completed delivery history",
        matched_category_count=1,
        known_potential_pounds=Decimal("0.00"),
        has_unknown_capacity=True,
        food_matches_snapshot=[
            {
                "food_category_code": "produce",
                "quantity_fit": "capacity_unknown",
            }
        ],
    )

    assert candidate.rank == 1
    assert candidate.recipient_name == "Community Food Pantry"
    assert candidate.has_unknown_capacity is True
