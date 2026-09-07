from datetime import date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.delivery import Delivery
from app.models.recipient_site import RecipientSite
from app.schemas.delivery_queue import (
    DeliveryQueueRead,
    QueueRecipientRead,
)
from app.services.delivery_queue import (
    TIE_WINDOW_DAYS,
    QueueCandidate,
    rank_delivery_queue,
)

router = APIRouter(
    prefix="/delivery-queue",
    tags=["delivery queue"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
LOCAL_TIMEZONE = ZoneInfo("America/Los_Angeles")


@router.get(
    "",
    response_model=DeliveryQueueRead,
)
def get_delivery_queue(
    db: DatabaseSession,
    as_of: date | None = None,
) -> DeliveryQueueRead:
    report_date = as_of if as_of is not None else datetime.now(LOCAL_TIMEZONE).date()
    window_start = report_date - timedelta(days=29)

    delivery_join = and_(
        Delivery.recipient_site_id == RecipientSite.id,
        Delivery.delivery_date <= report_date,
    )
    recent_delivery = Delivery.delivery_date >= window_start

    rows = db.execute(
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
            RecipientSite.is_active.is_(True),
            RecipientSite.is_fallback.is_(False),
        )
        .group_by(
            RecipientSite.id,
            RecipientSite.name,
            RecipientSite.priority,
        )
    ).mappings()

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
                days_since_last_delivery=(days_since_last_delivery),
                is_overdue=is_overdue,
                deliveries_last_30_days=row["deliveries_last_30_days"],
                pounds_last_30_days=float(row["pounds_last_30_days"]),
                total_deliveries=row["total_deliveries"],
                total_pounds=float(row["total_pounds"]),
                reason=reason,
            )
        )

    ranked_candidates = rank_delivery_queue(candidates)

    recipients = [
        QueueRecipientRead(
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
        )
        for rank, candidate in enumerate(
            ranked_candidates,
            start=1,
        )
    ]

    return DeliveryQueueRead(
        as_of_date=report_date,
        tie_window_days=TIE_WINDOW_DAYS,
        total=len(recipients),
        recipients=recipients,
    )
