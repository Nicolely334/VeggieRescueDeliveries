import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.donation_allocation import DonationAllocation
from app.models.donation_allocation_item import DonationAllocationItem
from app.models.donation_offer import DonationOffer
from app.models.donation_offer_item import DonationOfferItem
from app.models.recipient_site import RecipientSite
from app.models.recommendation_candidate import RecommendationCandidate
from app.models.recommendation_run import RecommendationRun
from app.schemas.donation_allocation import DonationAllocationCreate


class AllocationNotFoundError(Exception):
    pass


class AllocationConflictError(Exception):
    pass


def _as_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _candidate_matches_by_category(
    candidate: RecommendationCandidate,
) -> dict[str, dict[str, object]]:
    return {
        str(match["food_category_code"]): match
        for match in candidate.food_matches_snapshot
    }


def create_donation_allocation(
    db: Session,
    *,
    offer_id: uuid.UUID,
    allocation_data: DonationAllocationCreate,
) -> DonationAllocation:
    offer = db.get(
        DonationOffer,
        offer_id,
        with_for_update=True,
    )

    if offer is None:
        raise AllocationNotFoundError("donation offer not found")

    if offer.status != "open":
        raise AllocationConflictError(
            "allocations can only be added to an open donation offer"
        )

    recommendation_run = db.get(
        RecommendationRun,
        allocation_data.recommendation_run_id,
    )

    if recommendation_run is None:
        raise AllocationNotFoundError("recommendation run not found")

    if recommendation_run.donation_offer_id != offer_id:
        raise AllocationConflictError(
            "recommendation run does not belong to this donation offer"
        )

    recipient = db.get(
        RecipientSite,
        allocation_data.recipient_site_id,
    )

    if recipient is None:
        raise AllocationNotFoundError("recipient site not found")

    if not recipient.is_active:
        raise AllocationConflictError("recipient site is inactive")

    candidate = db.scalar(
        select(RecommendationCandidate).where(
            RecommendationCandidate.recommendation_run_id
            == allocation_data.recommendation_run_id,
            RecommendationCandidate.recipient_site_id
            == allocation_data.recipient_site_id,
        )
    )

    if candidate is None and not allocation_data.is_override:
        raise AllocationConflictError(
            "recipient was not included in this recommendation run; "
            "record the decision as an override"
        )

    offered_rows = db.execute(
        select(
            DonationOfferItem.food_category_code,
            DonationOfferItem.pounds,
        ).where(
            DonationOfferItem.donation_offer_id == offer_id,
        )
    ).all()
    offered_pounds = {
        food_category_code: pounds
        for food_category_code, pounds in offered_rows
    }

    if not offered_pounds:
        raise AllocationConflictError("donation offer has no food items")

    existing_rows = db.execute(
        select(
            DonationAllocationItem.food_category_code,
            func.sum(DonationAllocationItem.pounds),
        )
        .join(
            DonationAllocation,
            DonationAllocation.id
            == DonationAllocationItem.donation_allocation_id,
        )
        .where(
            DonationAllocation.donation_offer_id == offer_id,
            DonationAllocation.status != "cancelled",
        )
        .group_by(DonationAllocationItem.food_category_code)
    ).all()
    allocated_pounds: defaultdict[str, Decimal] = defaultdict(
        lambda: Decimal("0")
    )

    for food_category_code, pounds in existing_rows:
        allocated_pounds[food_category_code] = pounds

    requested_pounds = {
        item.food_category_code: _as_decimal(item.pounds)
        for item in allocation_data.items
    }

    for food_category_code, pounds in requested_pounds.items():
        if food_category_code not in offered_pounds:
            raise AllocationConflictError(
                f"food category {food_category_code!r} is not part of this offer"
            )

        remaining_pounds = (
            offered_pounds[food_category_code]
            - allocated_pounds[food_category_code]
        )

        if pounds > remaining_pounds:
            raise AllocationConflictError(
                f"allocation exceeds the remaining {food_category_code} pounds"
            )

    if candidate is not None and not allocation_data.is_override:
        matches_by_category = _candidate_matches_by_category(candidate)

        for food_category_code, pounds in requested_pounds.items():
            match = matches_by_category.get(food_category_code)

            if match is None:
                raise AllocationConflictError(
                    f"recipient was not recommended for {food_category_code}; "
                    "record the decision as an override"
                )

            potential_pounds = match.get("potential_pounds")

            if (
                potential_pounds is not None
                and pounds > Decimal(str(potential_pounds))
            ):
                raise AllocationConflictError(
                    f"allocation exceeds the recommended {food_category_code} capacity; "
                    "record the decision as an override"
                )

    allocation_id = uuid.uuid4()
    allocation = DonationAllocation(
        id=allocation_id,
        donation_offer_id=offer_id,
        recommendation_run_id=(allocation_data.recommendation_run_id),
        recipient_site_id=allocation_data.recipient_site_id,
        status=("assigned" if allocation_data.driver_name else "planned"),
        is_override=allocation_data.is_override,
        override_reason=allocation_data.override_reason,
        driver_name=allocation_data.driver_name,
        vehicle_name=allocation_data.vehicle_name,
        notes=allocation_data.notes,
    )
    items = [
        DonationAllocationItem(
            id=uuid.uuid4(),
            donation_allocation_id=allocation_id,
            food_category_code=food_category_code,
            pounds=pounds,
        )
        for food_category_code, pounds in requested_pounds.items()
    ]

    db.add(allocation)
    db.add_all(items)

    for food_category_code, pounds in requested_pounds.items():
        allocated_pounds[food_category_code] += pounds

    if all(
        allocated_pounds[food_category_code] == pounds
        for food_category_code, pounds in offered_pounds.items()
    ):
        offer.status = "allocated"

    db.flush()
    return allocation
