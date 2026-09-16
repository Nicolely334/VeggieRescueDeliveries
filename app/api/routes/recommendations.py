import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.donation_delivery_queue import get_donation_delivery_queue
from app.db.session import get_db
from app.models.donation_offer_item import DonationOfferItem
from app.models.food_category import FoodCategory
from app.schemas.recommendation import RecommendationSnapshotCreated
from app.services.recommendation_snapshots import save_recommendation_snapshot

router = APIRouter(
    prefix="/donation-offers",
    tags=["recommendations"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def load_offered_items_snapshot(
    db: Session,
    offer_id: uuid.UUID,
) -> list[dict[str, object]]:
    item_rows = db.execute(
        select(
            DonationOfferItem,
            FoodCategory.name.label("category_name"),
        )
        .join(
            FoodCategory,
            FoodCategory.code == DonationOfferItem.food_category_code,
        )
        .where(
            DonationOfferItem.donation_offer_id == offer_id,
        )
        .order_by(
            DonationOfferItem.food_category_code,
        )
    ).all()

    return [
        {
            "food_category_code": item.food_category_code,
            "category_name": category_name,
            "pounds": float(item.pounds),
        }
        for item, category_name in item_rows
    ]


@router.post(
    "/{offer_id}/recommendations",
    response_model=RecommendationSnapshotCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_recommendation_snapshot(
    offer_id: uuid.UUID,
    db: DatabaseSession,
    as_of: date | None = None,
) -> RecommendationSnapshotCreated:
    queue = get_donation_delivery_queue(
        offer_id=offer_id,
        db=db,
        as_of=as_of,
    )
    offered_items_snapshot = load_offered_items_snapshot(
        db=db,
        offer_id=offer_id,
    )

    try:
        run = save_recommendation_snapshot(
            db,
            queue=queue,
            offered_items_snapshot=offered_items_snapshot,
        )
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="recommendation snapshot could not be saved",
        ) from error

    return RecommendationSnapshotCreated(
        recommendation_run_id=run.id,
        policy_version=run.policy_version,
        queue=queue,
    )