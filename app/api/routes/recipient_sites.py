import uuid
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.food_category import FoodCategory
from app.models.recipient_food_preference import RecipientFoodPreference
from app.models.recipient_site import RecipientSite
from app.schemas.recipient_site import (
    RecipientSiteCreate,
    RecipientSiteListRead,
    RecipientSiteRead,
)

router = APIRouter(
    prefix="/recipient-sites",
    tags=["recipient sites"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=RecipientSiteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recipient_site(
    recipient_data: RecipientSiteCreate,
    db: DatabaseSession,
) -> RecipientSite:
    recipient_site = RecipientSite(**recipient_data.model_dump())

    db.add(recipient_site)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="recipient site could not be created",
        ) from error

    db.refresh(recipient_site)
    return recipient_site


@router.get(
    "",
    response_model=list[RecipientSiteListRead],
)
def list_recipient_sites(
    db: DatabaseSession,
    include_inactive: bool = False,
) -> list[RecipientSiteListRead]:
    statement = select(RecipientSite).order_by(RecipientSite.name)

    if not include_inactive:
        statement = statement.where(RecipientSite.is_active.is_(True))

    sites = list(db.scalars(statement).all())
    if not sites:
        return []

    preferences_by_site: dict[uuid.UUID, list[tuple[str, float | None]]] = defaultdict(list)
    preference_rows = db.execute(
        select(
            RecipientFoodPreference.recipient_site_id,
            FoodCategory.name,
            RecipientFoodPreference.maximum_pounds,
        )
        .join(
            FoodCategory,
            FoodCategory.code == RecipientFoodPreference.food_category_code,
        )
        .where(RecipientFoodPreference.recipient_site_id.in_([site.id for site in sites]))
    ).all()

    for site_id, category_name, maximum_pounds in preference_rows:
        preferences_by_site[site_id].append(
            (
                category_name,
                float(maximum_pounds) if maximum_pounds is not None else None,
            )
        )

    result: list[RecipientSiteListRead] = []
    for site in sites:
        preferences = preferences_by_site[site.id]
        known_capacities = [capacity for _, capacity in preferences if capacity is not None]
        result.append(
            RecipientSiteListRead.model_validate(site).model_copy(
                update={
                    "capacity_level": max(known_capacities) if known_capacities else None,
                    "food_type": sorted({category_name for category_name, _ in preferences}),
                }
            )
        )

    return result
