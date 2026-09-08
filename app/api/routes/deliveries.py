import uuid
from collections import defaultdict
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.delivery import Delivery
from app.models.delivery_item import DeliveryItem
from app.models.food_category import FoodCategory
from app.models.recipient_site import RecipientSite
from app.schemas.delivery import (
    DeliveryItemRead,
    DeliveryListRead,
    DeliveryRead,
)

router = APIRouter(
    prefix="/deliveries",
    tags=["deliveries"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=DeliveryListRead,
)
def list_deliveries(
    db: DatabaseSession,
    recipient_site_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Literal["oldest", "newest"] = "newest",
) -> DeliveryListRead:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to",
        )

    filters = []

    if recipient_site_id is not None:
        filters.append(Delivery.recipient_site_id == recipient_site_id)

    if date_from is not None:
        filters.append(Delivery.delivery_date >= date_from)

    if date_to is not None:
        filters.append(Delivery.delivery_date <= date_to)

    total = db.scalar(select(func.count(Delivery.id)).where(*filters)) or 0

    delivery_order = (
        Delivery.delivery_date.asc()
        if sort == "oldest"
        else Delivery.delivery_date.desc()
    )

    delivery_rows = db.execute(
        select(
            Delivery,
            RecipientSite.name.label("recipient_name"),
        )
        .join(
            RecipientSite,
            RecipientSite.id == Delivery.recipient_site_id,
        )
        .where(*filters)
        .order_by(
            delivery_order,
            Delivery.id.asc() if sort == "oldest" else Delivery.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    delivery_ids = [delivery.id for delivery, _recipient_name in delivery_rows]

    items_by_delivery: dict[
        uuid.UUID,
        list[DeliveryItemRead],
    ] = defaultdict(list)
    weights_by_delivery: dict[
        uuid.UUID,
        dict[str, float],
    ] = defaultdict(dict)

    if delivery_ids:
        item_rows = db.execute(
            select(
                DeliveryItem.delivery_id,
                DeliveryItem.food_category_code,
                FoodCategory.name,
                DeliveryItem.pounds,
            )
            .join(
                FoodCategory,
                FoodCategory.code == DeliveryItem.food_category_code,
            )
            .where(DeliveryItem.delivery_id.in_(delivery_ids))
            .order_by(
                DeliveryItem.delivery_id,
                FoodCategory.name,
            )
        ).all()

        for (
            delivery_id,
            category_code,
            category_name,
            pounds,
        ) in item_rows:
            pounds_value = float(pounds)

            items_by_delivery[delivery_id].append(
                DeliveryItemRead(
                    category_code=category_code,
                    category_name=category_name,
                    pounds=pounds_value,
                )
            )
            weights_by_delivery[delivery_id][category_code] = pounds_value

    deliveries: list[DeliveryRead] = []

    for delivery, recipient_name in delivery_rows:
        category_weights = weights_by_delivery.get(
            delivery.id,
            {},
        )

        deliveries.append(
            DeliveryRead(
                id=delivery.id,
                recipient_site_id=delivery.recipient_site_id,
                delivery_date=delivery.delivery_date,
                recipient=recipient_name,
                location=delivery.recipient_location or "",
                produce_pounds=category_weights.get("produce"),
                packaged_pounds=category_weights.get("packaged"),
                driver=delivery.driver_name or "",
                vehicle=delivery.vehicle_name or "",
                total_pounds=float(delivery.total_pounds),
                items=items_by_delivery.get(delivery.id, []),
                source_recipient_name=(delivery.source_recipient_name),
                created_at=delivery.created_at,
                status="completed",
            )
        )

    return DeliveryListRead(
        total=total,
        deliveries=deliveries,
        limit=limit,
        offset=offset,
    )
