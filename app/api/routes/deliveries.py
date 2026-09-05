from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.import_row import ImportRow
from app.schemas.delivery import DeliveryListRead, DeliveryRead

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


def display_value(value: object) -> str:
    return "" if value is None else str(value).strip()


def numeric_value(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sort_key(delivery: DeliveryRead) -> tuple[date, str]:
    try:
        parsed_date = datetime.fromisoformat(delivery.delivery_date).date()
    except ValueError:
        parsed_date = date.min
    return parsed_date, delivery.recipient.lower()


@router.get("", response_model=DeliveryListRead)
def list_deliveries(db: Session = Depends(get_db)) -> DeliveryListRead:
    rows = db.scalars(
        select(ImportRow).where(ImportRow.status != "rejected")
    ).all()
    deliveries = [
        DeliveryRead(
            id=str(row.id),
            delivery_date=display_value(row.raw_data.get("B")),
            recipient=display_value(row.raw_data.get("C")),
            location=display_value(row.raw_data.get("D")),
            produce_pounds=numeric_value(row.raw_data.get("G")),
            packaged_pounds=numeric_value(row.raw_data.get("H")),
            driver=display_value(row.raw_data.get("E")),
            vehicle=display_value(row.raw_data.get("F")),
            status=row.status,
        )
        for row in rows
    ]
    deliveries.sort(key=sort_key, reverse=True)
    return DeliveryListRead(total=len(deliveries), deliveries=deliveries)