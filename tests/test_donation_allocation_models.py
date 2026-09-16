import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.models.donation_allocation import DonationAllocation
from app.models.donation_allocation_item import DonationAllocationItem


def test_donation_allocation_has_audit_and_assignment_columns() -> None:
    table = DonationAllocation.__table__

    assert table.c.donation_offer_id.nullable is False
    assert table.c.recommendation_run_id.nullable is False
    assert table.c.recipient_site_id.nullable is False
    assert table.c.status.type.length == 20
    assert table.c.is_override.nullable is False
    assert table.c.driver_name.type.length == 200
    assert table.c.vehicle_name.type.length == 200

    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_donation_allocations_valid_status" in constraint_names
    assert (
        "ck_donation_allocations_override_reason_required"
        in constraint_names
    )

    index_names = {
        index.name
        for index in table.indexes
        if isinstance(index, Index)
    }

    assert (
        "uq_donation_allocations_active_offer_recipient"
        in index_names
    )


def test_donation_allocation_item_has_quantity_constraints() -> None:
    table = DonationAllocationItem.__table__
    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert table.c.pounds.nullable is False
    assert "allocation_food_category" in unique_constraint_names
    assert (
        "ck_donation_allocation_items_positive_pounds"
        in check_constraint_names
    )


def test_allocation_models_preserve_operational_metadata() -> None:
    now = datetime.now(UTC)
    allocation_id = uuid.uuid4()
    allocation = DonationAllocation(
        id=allocation_id,
        donation_offer_id=uuid.uuid4(),
        recommendation_run_id=uuid.uuid4(),
        recipient_site_id=uuid.uuid4(),
        status="assigned",
        is_override=True,
        override_reason="Recipient had urgent need",
        driver_name="Taylor",
        vehicle_name="Van",
        notes="Call before arrival",
        created_at=now,
        updated_at=now,
    )
    item = DonationAllocationItem(
        id=uuid.uuid4(),
        donation_allocation_id=allocation_id,
        food_category_code="produce",
        pounds=Decimal("50.00"),
        created_at=now,
    )

    assert allocation.status == "assigned"
    assert allocation.is_override is True
    assert allocation.override_reason == "Recipient had urgent need"
    assert item.donation_allocation_id == allocation.id
    assert item.pounds == Decimal("50.00")
