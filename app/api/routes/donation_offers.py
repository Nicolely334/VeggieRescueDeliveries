import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.donation_offer import DonationOffer
from app.models.donation_offer_item import DonationOfferItem
from app.models.farm import Farm
from app.models.food_category import FoodCategory
from app.schemas.donation_offer import (
    DonationOfferCreate,
    DonationOfferItemRead,
    DonationOfferListRead,
    DonationOfferRead,
    DonationOfferStatus,
)

router = APIRouter(
    prefix="/donation-offers",
    tags=["donation offers"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def build_offer_read(
    offer: DonationOffer,
    farm_name: str,
    item_rows: Sequence[tuple[DonationOfferItem, str]],
) -> DonationOfferRead:
    items = [
        DonationOfferItemRead(
            id=item.id,
            food_category_code=item.food_category_code,
            category_name=category_name,
            pounds=float(item.pounds),
            created_at=item.created_at,
        )
        for item, category_name in item_rows
    ]

    total_pounds = sum(item.pounds for item in items)

    return DonationOfferRead(
        id=offer.id,
        farm_id=offer.farm_id,
        farm_name=farm_name,
        status=offer.status,
        available_from=offer.available_from,
        pickup_by=offer.pickup_by,
        notes=offer.notes,
        total_pounds=total_pounds,
        items=items,
        created_at=offer.created_at,
        updated_at=offer.updated_at,
    )


def load_offer_read(
    db: Session,
    offer_id: uuid.UUID,
) -> DonationOfferRead | None:
    offer_row = db.execute(
        select(
            DonationOffer,
            Farm.name.label("farm_name"),
        )
        .join(
            Farm,
            Farm.id == DonationOffer.farm_id,
        )
        .where(DonationOffer.id == offer_id)
    ).one_or_none()

    if offer_row is None:
        return None

    offer, farm_name = offer_row

    item_rows = db.execute(
        select(
            DonationOfferItem,
            FoodCategory.name.label("category_name"),
        )
        .join(
            FoodCategory,
            FoodCategory.code == DonationOfferItem.food_category_code,
        )
        .where(DonationOfferItem.donation_offer_id == offer.id)
        .order_by(FoodCategory.name)
    ).all()

    return build_offer_read(
        offer=offer,
        farm_name=farm_name,
        item_rows=item_rows,
    )


@router.post(
    "",
    response_model=DonationOfferRead,
    status_code=status.HTTP_201_CREATED,
)
def create_donation_offer(
    offer_data: DonationOfferCreate,
    db: DatabaseSession,
) -> DonationOfferRead:
    farm = db.get(Farm, offer_data.farm_id)

    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="farm not found",
        )

    if not farm.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot create an offer for an inactive farm",
        )

    category_codes = {item.food_category_code for item in offer_data.items}

    active_category_codes = set(
        db.scalars(
            select(FoodCategory.code).where(
                FoodCategory.code.in_(category_codes),
                FoodCategory.is_active.is_(True),
            )
        ).all()
    )

    missing_category_codes = sorted(category_codes - active_category_codes)

    if missing_category_codes:
        raise HTTPException(
            status_code=422,
            detail={
                "message": ("one or more food categories are unavailable"),
                "food_category_codes": (missing_category_codes),
            },
        )

    offer_values = offer_data.model_dump(exclude={"items"})
    donation_offer = DonationOffer(**offer_values)

    try:
        db.add(donation_offer)
        db.flush()

        db.add_all(
            [
                DonationOfferItem(
                    donation_offer_id=donation_offer.id,
                    food_category_code=(item.food_category_code),
                    pounds=Decimal(str(item.pounds)),
                )
                for item in offer_data.items
            ]
        )

        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="donation offer could not be created",
        ) from error

    created_offer = load_offer_read(
        db=db,
        offer_id=donation_offer.id,
    )

    if created_offer is None:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail="created donation offer could not be loaded",
        )

    return created_offer


@router.get(
    "",
    response_model=DonationOfferListRead,
)
def list_donation_offers(
    db: DatabaseSession,
    farm_id: uuid.UUID | None = None,
    status_filter: Annotated[
        DonationOfferStatus | None,
        Query(alias="status"),
    ] = None,
    pickup_by_before: datetime | None = None,
    limit: Annotated[
        int,
        Query(ge=1, le=200),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> DonationOfferListRead:
    filters = []

    if farm_id is not None:
        filters.append(DonationOffer.farm_id == farm_id)

    if status_filter is not None:
        filters.append(DonationOffer.status == status_filter)

    if pickup_by_before is not None:
        filters.append(DonationOffer.pickup_by <= pickup_by_before)

    total = db.scalar(select(func.count(DonationOffer.id)).where(*filters)) or 0

    offer_rows = db.execute(
        select(
            DonationOffer,
            Farm.name.label("farm_name"),
        )
        .join(
            Farm,
            Farm.id == DonationOffer.farm_id,
        )
        .where(*filters)
        .order_by(
            DonationOffer.pickup_by.asc().nulls_last(),
            DonationOffer.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    offer_ids = [offer.id for offer, _farm_name in offer_rows]

    items_by_offer: dict[
        uuid.UUID,
        list[tuple[DonationOfferItem, str]],
    ] = defaultdict(list)

    if offer_ids:
        item_rows = db.execute(
            select(
                DonationOfferItem,
                FoodCategory.name.label("category_name"),
            )
            .join(
                FoodCategory,
                FoodCategory.code == DonationOfferItem.food_category_code,
            )
            .where(DonationOfferItem.donation_offer_id.in_(offer_ids))
            .order_by(
                DonationOfferItem.donation_offer_id,
                FoodCategory.name,
            )
        ).all()

        for item, category_name in item_rows:
            items_by_offer[item.donation_offer_id].append((item, category_name))

    offers = [
        build_offer_read(
            offer=offer,
            farm_name=farm_name,
            item_rows=items_by_offer.get(
                offer.id,
                [],
            ),
        )
        for offer, farm_name in offer_rows
    ]

    return DonationOfferListRead(
        total=total,
        offers=offers,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{offer_id}",
    response_model=DonationOfferRead,
)
def get_donation_offer(
    offer_id: uuid.UUID,
    db: DatabaseSession,
) -> DonationOfferRead:
    offer = load_offer_read(
        db=db,
        offer_id=offer_id,
    )

    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="donation offer not found",
        )

    return offer
