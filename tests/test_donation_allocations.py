import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.donation_allocations import (
    build_allocation_read,
    create_allocation,
)
from app.main import app
from app.models.donation_allocation import DonationAllocation
from app.models.donation_allocation_item import DonationAllocationItem
from app.models.donation_offer import DonationOffer
from app.models.recipient_site import RecipientSite
from app.models.recommendation_candidate import RecommendationCandidate
from app.models.recommendation_run import RecommendationRun
from app.schemas.donation_allocation import (
    DonationAllocationCreate,
    DonationAllocationRead,
)
from app.services.donation_allocations import (
    AllocationConflictError,
    create_donation_allocation,
)


def build_allocation_data(
    recommendation_run_id: uuid.UUID,
    recipient_site_id: uuid.UUID,
    *,
    pounds: float = 100.0,
    is_override: bool = False,
) -> DonationAllocationCreate:
    return DonationAllocationCreate(
        recommendation_run_id=recommendation_run_id,
        recipient_site_id=recipient_site_id,
        is_override=is_override,
        override_reason=("Urgent community need" if is_override else None),
        items=[
            {
                "food_category_code": "produce",
                "pounds": pounds,
            }
        ],
    )


def build_service_objects() -> tuple[
    uuid.UUID,
    DonationOffer,
    RecommendationRun,
    RecipientSite,
    RecommendationCandidate,
]:
    offer_id = uuid.uuid4()
    run_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    offer = DonationOffer(
        id=offer_id,
        farm_id=uuid.uuid4(),
        status="open",
    )
    run = RecommendationRun(
        id=run_id,
        donation_offer_id=offer_id,
        as_of_date=date(2026, 9, 15),
        policy_version="v1",
        tie_window_days=3,
        offered_total_pounds=Decimal("100.00"),
        offered_items_snapshot=[],
    )
    recipient = RecipientSite(
        id=recipient_id,
        name="Community Pantry",
        priority=3,
        is_active=True,
        is_fallback=False,
    )
    candidate = RecommendationCandidate(
        id=uuid.uuid4(),
        recommendation_run_id=run_id,
        recipient_site_id=recipient_id,
        food_matches_snapshot=[
            {
                "food_category_code": "produce",
                "potential_pounds": 100.0,
            }
        ],
    )
    return offer_id, offer, run, recipient, candidate


def configure_service_session(
    offer: DonationOffer,
    run: RecommendationRun,
    recipient: RecipientSite,
    candidate: RecommendationCandidate | None,
    *,
    existing_pounds: Decimal = Decimal("0"),
) -> Mock:
    db = Mock(spec=Session)

    def get_model(
        model: type[object],
        _identifier: object,
        **_options: object,
    ) -> object | None:
        if model is DonationOffer:
            return offer
        if model is RecommendationRun:
            return run
        if model is RecipientSite:
            return recipient
        return None

    offered_result = Mock()
    offered_result.all.return_value = [
        ("produce", Decimal("100.00")),
    ]
    existing_result = Mock()
    existing_result.all.return_value = (
        [("produce", existing_pounds)]
        if existing_pounds > 0
        else []
    )

    db.get.side_effect = get_model
    db.scalar.return_value = candidate
    db.execute.side_effect = [
        offered_result,
        existing_result,
    ]
    return db


def test_allocation_routes_are_registered() -> None:
    path = "/api/v1/donation-offers/{offer_id}/allocations"
    operations = app.openapi()["paths"][path]

    assert "post" in operations
    assert operations["post"]["responses"]["201"]
    assert "get" in operations


def test_create_donation_allocation_allocates_complete_offer() -> None:
    offer_id, offer, run, recipient, candidate = build_service_objects()
    db = configure_service_session(
        offer,
        run,
        recipient,
        candidate,
    )

    allocation = create_donation_allocation(
        db,
        offer_id=offer_id,
        allocation_data=build_allocation_data(
            run.id,
            recipient.id,
        ),
    )

    assert allocation.donation_offer_id == offer_id
    assert allocation.recipient_site_id == recipient.id
    assert allocation.status == "planned"
    assert offer.status == "allocated"
    db.add.assert_called_once_with(allocation)

    created_items = db.add_all.call_args.args[0]
    assert len(created_items) == 1
    assert created_items[0].food_category_code == "produce"
    assert created_items[0].pounds == Decimal("100.0")
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()


def test_allocation_cannot_exceed_remaining_offer() -> None:
    offer_id, offer, run, recipient, candidate = build_service_objects()
    db = configure_service_session(
        offer,
        run,
        recipient,
        candidate,
        existing_pounds=Decimal("80.00"),
    )

    with pytest.raises(
        AllocationConflictError,
        match="exceeds the remaining produce pounds",
    ):
        create_donation_allocation(
            db,
            offer_id=offer_id,
            allocation_data=build_allocation_data(
                run.id,
                recipient.id,
                pounds=25.0,
            ),
        )

    db.add.assert_not_called()


def test_unrecommended_recipient_requires_override() -> None:
    offer_id, offer, run, recipient, _candidate = build_service_objects()
    db = configure_service_session(
        offer,
        run,
        recipient,
        None,
    )

    with pytest.raises(
        AllocationConflictError,
        match="record the decision as an override",
    ):
        create_donation_allocation(
            db,
            offer_id=offer_id,
            allocation_data=build_allocation_data(
                run.id,
                recipient.id,
            ),
        )


def test_override_allows_unrecommended_recipient() -> None:
    offer_id, offer, run, recipient, _candidate = build_service_objects()
    db = configure_service_session(
        offer,
        run,
        recipient,
        None,
    )

    allocation = create_donation_allocation(
        db,
        offer_id=offer_id,
        allocation_data=build_allocation_data(
            run.id,
            recipient.id,
            is_override=True,
        ),
    )

    assert allocation.is_override is True
    assert allocation.override_reason == "Urgent community need"


def test_build_allocation_read_calculates_total() -> None:
    now = datetime.now(UTC)
    allocation_id = uuid.uuid4()
    allocation = DonationAllocation(
        id=allocation_id,
        donation_offer_id=uuid.uuid4(),
        recommendation_run_id=uuid.uuid4(),
        recipient_site_id=uuid.uuid4(),
        status="planned",
        is_override=False,
        override_reason=None,
        driver_name=None,
        vehicle_name=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    item = DonationAllocationItem(
        id=uuid.uuid4(),
        donation_allocation_id=allocation_id,
        food_category_code="produce",
        pounds=Decimal("75.50"),
        created_at=now,
    )

    response = build_allocation_read(
        allocation=allocation,
        recipient_name="Community Pantry",
        item_rows=[(item, "Produce")],
    )

    assert response.total_pounds == 75.5
    assert response.recipient_name == "Community Pantry"


def test_create_allocation_route_rolls_back_conflict() -> None:
    offer_id = uuid.uuid4()
    allocation_data = build_allocation_data(
        uuid.uuid4(),
        uuid.uuid4(),
    )
    db = Mock(spec=Session)

    with (
        patch(
            "app.api.routes.donation_allocations.create_donation_allocation",
            side_effect=AllocationConflictError("offer is already allocated"),
        ),
        pytest.raises(HTTPException) as error_info,
    ):
        create_allocation(
            offer_id=offer_id,
            allocation_data=allocation_data,
            db=db,
        )

    assert error_info.value.status_code == status.HTTP_409_CONFLICT
    assert error_info.value.detail == "offer is already allocated"
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_create_allocation_route_commits() -> None:
    offer_id = uuid.uuid4()
    allocation_data = build_allocation_data(
        uuid.uuid4(),
        uuid.uuid4(),
    )
    allocation = Mock(id=uuid.uuid4())
    response = Mock(spec=DonationAllocationRead)
    db = Mock(spec=Session)

    with (
        patch(
            "app.api.routes.donation_allocations.create_donation_allocation",
            return_value=allocation,
        ),
        patch(
            "app.api.routes.donation_allocations.load_allocation_read",
            return_value=response,
        ),
    ):
        result = create_allocation(
            offer_id=offer_id,
            allocation_data=allocation_data,
            db=db,
        )

    assert result is response
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
