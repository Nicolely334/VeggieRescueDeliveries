import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.delivery import Delivery
from app.models.donation_offer import DonationOffer
from app.models.donation_offer_item import DonationOfferItem
from app.models.food_category import FoodCategory
from app.models.recipient_food_preference import (
    RecipientFoodPreference,
)
from app.models.recipient_site import RecipientSite
from app.schemas.donation_delivery_queue import (
    DonationDeliveryQueueRead,
    DonationQueueFoodMatchRead,
    DonationQueueRecipientRead,
)
from app.services.delivery_queue import (
    TIE_WINDOW_DAYS,
    QueueCandidate,
    rank_delivery_queue,
)
from app.services.donation_matching import match_donation_food

router = APIRouter(
    prefix="/donation-offers",
    tags=["donation delivery queue"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
LOCAL_TIMEZONE = ZoneInfo("America/Los_Angeles")


@router.get(
    "/{offer_id}/delivery-queue",
    response_model=DonationDeliveryQueueRead,
)
def get_donation_delivery_queue(
    offer_id: uuid.UUID,
    db: DatabaseSession,
    as_of: date | None = None,
) -> DonationDeliveryQueueRead:
    offer = db.get(
        DonationOffer,
        offer_id,
    )

    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="donation offer not found",
        )

    if offer.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="delivery queue is only available for open donation offers",
        )

    offer_item_rows = db.execute(
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

    if not offer_item_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="donation offer has no food items",
        )

    offered_pounds_by_category = {
        item.food_category_code: item.pounds for item, _category_name in offer_item_rows
    }
    category_names = {
        item.food_category_code: category_name for item, category_name in offer_item_rows
    }

    preference_rows = db.execute(
        select(
            RecipientFoodPreference.recipient_site_id,
            RecipientFoodPreference.food_category_code,
            RecipientFoodPreference.maximum_pounds,
        )
        .join(
            RecipientSite,
            RecipientSite.id == RecipientFoodPreference.recipient_site_id,
        )
        .where(
            RecipientSite.is_active.is_(True),
            RecipientSite.is_fallback.is_(False),
            RecipientFoodPreference.food_category_code.in_(list(offered_pounds_by_category)),
        )
    ).all()

    preferences_by_recipient: dict[
        uuid.UUID,
        dict[str, Decimal | None],
    ] = defaultdict(dict)

    for (
        recipient_site_id,
        food_category_code,
        maximum_pounds,
    ) in preference_rows:
        preferences_by_recipient[recipient_site_id][food_category_code] = maximum_pounds

    report_date = as_of if as_of is not None else datetime.now(LOCAL_TIMEZONE).date()
    window_start = report_date - timedelta(days=29)

    eligible_recipient_ids = list(preferences_by_recipient)

    if not eligible_recipient_ids:
        return DonationDeliveryQueueRead(
            donation_offer_id=offer.id,
            offer_status="open",
            as_of_date=report_date,
            tie_window_days=TIE_WINDOW_DAYS,
            offered_category_count=len(offered_pounds_by_category),
            total_offered_pounds=float(
                sum(
                    offered_pounds_by_category.values(),
                    Decimal("0"),
                )
            ),
            total=0,
            recipients=[],
        )

    delivery_join = and_(
        Delivery.recipient_site_id == RecipientSite.id,
        Delivery.delivery_date <= report_date,
    )
    recent_delivery = Delivery.delivery_date >= window_start

    rows = (
        db.execute(
            select(
                RecipientSite.id.label("recipient_site_id"),
                RecipientSite.name,
                RecipientSite.priority,
                func.max(Delivery.delivery_date).label("last_delivery_date"),
                func.count(Delivery.id).filter(recent_delivery).label("deliveries_last_30_days"),
                func.coalesce(
                    func.sum(Delivery.total_pounds).filter(recent_delivery),
                    0,
                ).label("pounds_last_30_days"),
                func.count(Delivery.id).label("total_deliveries"),
                func.coalesce(
                    func.sum(Delivery.total_pounds),
                    0,
                ).label("total_pounds"),
            )
            .select_from(RecipientSite)
            .outerjoin(
                Delivery,
                delivery_join,
            )
            .where(
                RecipientSite.id.in_(eligible_recipient_ids),
                RecipientSite.is_active.is_(True),
                RecipientSite.is_fallback.is_(False),
            )
            .group_by(
                RecipientSite.id,
                RecipientSite.name,
                RecipientSite.priority,
            )
        )
        .mappings()
        .all()
    )

    candidates: list[QueueCandidate] = []

    for row in rows:
        last_delivery_date = row["last_delivery_date"]

        if last_delivery_date is None:
            days_since_last_delivery = None
            is_overdue = True
            reason = "No completed delivery history"
        else:
            days_since_last_delivery = (report_date - last_delivery_date).days
            is_overdue = days_since_last_delivery >= 30

            if is_overdue:
                reason = f"Overdue: {days_since_last_delivery} days since last delivery"
            else:
                reason = f"{days_since_last_delivery} days since last delivery"

        candidates.append(
            QueueCandidate(
                recipient_site_id=row["recipient_site_id"],
                name=row["name"],
                priority=row["priority"],
                last_delivery_date=last_delivery_date,
                days_since_last_delivery=days_since_last_delivery,
                is_overdue=is_overdue,
                deliveries_last_30_days=(row["deliveries_last_30_days"]),
                pounds_last_30_days=float(row["pounds_last_30_days"]),
                total_deliveries=row["total_deliveries"],
                total_pounds=float(row["total_pounds"]),
                reason=reason,
            )
        )

    ranked_candidates = rank_delivery_queue(candidates)
    recipients: list[DonationQueueRecipientRead] = []

    for rank, candidate in enumerate(
        ranked_candidates,
        start=1,
    ):
        matches = match_donation_food(
            offered_pounds_by_category=(offered_pounds_by_category),
            maximum_pounds_by_category=(preferences_by_recipient[candidate.recipient_site_id]),
        )

        known_potential_pounds = sum(
            (match.potential_pounds for match in matches if match.potential_pounds is not None),
            Decimal("0"),
        )

        recipients.append(
            DonationQueueRecipientRead(
                rank=rank,
                recipient_site_id=candidate.recipient_site_id,
                name=candidate.name,
                priority=candidate.priority,
                last_delivery_date=(candidate.last_delivery_date),
                days_since_last_delivery=(candidate.days_since_last_delivery),
                is_overdue=candidate.is_overdue,
                deliveries_last_30_days=(candidate.deliveries_last_30_days),
                pounds_last_30_days=(candidate.pounds_last_30_days),
                total_deliveries=candidate.total_deliveries,
                total_pounds=candidate.total_pounds,
                reason=candidate.reason,
                matched_category_count=len(matches),
                known_potential_pounds=float(known_potential_pounds),
                has_unknown_capacity=any(match.potential_pounds is None for match in matches),
                food_matches=[
                    DonationQueueFoodMatchRead(
                        food_category_code=(match.food_category_code),
                        category_name=category_names[match.food_category_code],
                        offered_pounds=float(match.offered_pounds),
                        maximum_pounds=(
                            float(match.maximum_pounds)
                            if match.maximum_pounds is not None
                            else None
                        ),
                        potential_pounds=(
                            float(match.potential_pounds)
                            if match.potential_pounds is not None
                            else None
                        ),
                        quantity_fit=match.quantity_fit,
                    )
                    for match in matches
                ],
            )
        )

    return DonationDeliveryQueueRead(
        donation_offer_id=offer.id,
        offer_status="open",
        as_of_date=report_date,
        tie_window_days=TIE_WINDOW_DAYS,
        offered_category_count=len(offered_pounds_by_category),
        total_offered_pounds=float(
            sum(
                offered_pounds_by_category.values(),
                Decimal("0"),
            )
        ),
        total=len(recipients),
        recipients=recipients,
    )
