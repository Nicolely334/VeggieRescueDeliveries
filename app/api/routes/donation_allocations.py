import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.donation_allocation import DonationAllocation
from app.models.donation_allocation_item import DonationAllocationItem
from app.models.donation_offer import DonationOffer
from app.models.food_category import FoodCategory
from app.models.recipient_site import RecipientSite
from app.schemas.donation_allocation import (
    DonationAllocationCreate,
    DonationAllocationItemRead,
    DonationAllocationListRead,
    DonationAllocationRead,
)
from app.services.donation_allocations import (
    AllocationConflictError,
    AllocationNotFoundError,
    create_donation_allocation,
)

router = APIRouter(
    prefix="/donation-offers",
    tags=["donation allocations"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def build_allocation_read(
    allocation: DonationAllocation,
    recipient_name: str,
    item_rows: Sequence[tuple[DonationAllocationItem, str]],
) -> DonationAllocationRead:
    items = [
        DonationAllocationItemRead(
            id=item.id,
            food_category_code=item.food_category_code,
            category_name=category_name,
            pounds=float(item.pounds),
            created_at=item.created_at,
        )
        for item, category_name in item_rows
    ]

    return DonationAllocationRead(
        id=allocation.id,
        donation_offer_id=allocation.donation_offer_id,
        recommendation_run_id=allocation.recommendation_run_id,
        recipient_site_id=allocation.recipient_site_id,
        recipient_name=recipient_name,
        status=allocation.status,
        is_override=allocation.is_override,
        override_reason=allocation.override_reason,
        driver_name=allocation.driver_name,
        vehicle_name=allocation.vehicle_name,
        notes=allocation.notes,
        total_pounds=sum(item.pounds for item in items),
        items=items,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


def load_allocation_read(
    db: Session,
    allocation_id: uuid.UUID,
) -> DonationAllocationRead | None:
    allocation_row = db.execute(
        select(
            DonationAllocation,
            RecipientSite.name.label("recipient_name"),
        )
        .join(
            RecipientSite,
            RecipientSite.id == DonationAllocation.recipient_site_id,
        )
        .where(DonationAllocation.id == allocation_id)
    ).one_or_none()

    if allocation_row is None:
        return None

    allocation, recipient_name = allocation_row
    item_rows = db.execute(
        select(
            DonationAllocationItem,
            FoodCategory.name.label("category_name"),
        )
        .join(
            FoodCategory,
            FoodCategory.code
            == DonationAllocationItem.food_category_code,
        )
        .where(
            DonationAllocationItem.donation_allocation_id == allocation_id,
        )
        .order_by(FoodCategory.name)
    ).all()

    return build_allocation_read(
        allocation=allocation,
        recipient_name=recipient_name,
        item_rows=item_rows,
    )


@router.post(
    "/{offer_id}/allocations",
    response_model=DonationAllocationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_allocation(
    offer_id: uuid.UUID,
    allocation_data: DonationAllocationCreate,
    db: DatabaseSession,
) -> DonationAllocationRead:
    try:
        allocation = create_donation_allocation(
            db,
            offer_id=offer_id,
            allocation_data=allocation_data,
        )
        db.commit()
    except AllocationNotFoundError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except AllocationConflictError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="donation allocation could not be created",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="donation allocation could not be saved",
        ) from error

    created_allocation = load_allocation_read(
        db=db,
        allocation_id=allocation.id,
    )

    if created_allocation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="created donation allocation could not be loaded",
        )

    return created_allocation


@router.get(
    "/{offer_id}/allocations",
    response_model=DonationAllocationListRead,
)
def list_allocations(
    offer_id: uuid.UUID,
    db: DatabaseSession,
) -> DonationAllocationListRead:
    offer = db.get(DonationOffer, offer_id)

    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="donation offer not found",
        )

    allocation_rows = db.execute(
        select(
            DonationAllocation,
            RecipientSite.name.label("recipient_name"),
        )
        .join(
            RecipientSite,
            RecipientSite.id == DonationAllocation.recipient_site_id,
        )
        .where(DonationAllocation.donation_offer_id == offer_id)
        .order_by(DonationAllocation.created_at, DonationAllocation.id)
    ).all()
    allocation_ids = [
        allocation.id for allocation, _recipient_name in allocation_rows
    ]
    items_by_allocation: defaultdict[
        uuid.UUID,
        list[tuple[DonationAllocationItem, str]],
    ] = defaultdict(list)

    if allocation_ids:
        item_rows = db.execute(
            select(
                DonationAllocationItem,
                FoodCategory.name.label("category_name"),
            )
            .join(
                FoodCategory,
                FoodCategory.code
                == DonationAllocationItem.food_category_code,
            )
            .where(
                DonationAllocationItem.donation_allocation_id.in_(
                    allocation_ids
                )
            )
            .order_by(
                DonationAllocationItem.donation_allocation_id,
                FoodCategory.name,
            )
        ).all()

        for item, category_name in item_rows:
            items_by_allocation[item.donation_allocation_id].append(
                (item, category_name)
            )

    allocations = [
        build_allocation_read(
            allocation=allocation,
            recipient_name=recipient_name,
            item_rows=items_by_allocation.get(allocation.id, []),
        )
        for allocation, recipient_name in allocation_rows
    ]

    return DonationAllocationListRead(
        donation_offer_id=offer_id,
        total=len(allocations),
        total_allocated_pounds=sum(
            allocation.total_pounds
            for allocation in allocations
            if allocation.status != "cancelled"
        ),
        allocations=allocations,
    )
