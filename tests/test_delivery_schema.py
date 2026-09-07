import uuid
from datetime import date, datetime, timezone

from app.schemas.delivery import (
    DeliveryItemRead,
    DeliveryListRead,
    DeliveryRead,
)


def test_delivery_list_schema() -> None:
    delivery = DeliveryRead(
        id=uuid.uuid4(),
        recipient_site_id=uuid.uuid4(),
        delivery_date=date(2026, 8, 31),
        recipient="Unity Shoppe - SB",
        location="SB/Goleta",
        produce_pounds=125,
        packaged_pounds=None,
        driver="Kevin",
        vehicle="Van",
        total_pounds=125,
        items=[
            DeliveryItemRead(
                category_code="produce",
                category_name="Produce",
                pounds=125,
            )
        ],
        source_recipient_name="Unity Shoppe",
        created_at=datetime.now(timezone.utc),
        status="completed",
    )

    response = DeliveryListRead(
        total=1,
        deliveries=[delivery],
        limit=50,
        offset=0,
    )

    assert response.total == 1
    assert response.deliveries[0].recipient == (
        "Unity Shoppe - SB"
    )
    assert response.deliveries[0].produce_pounds == 125
    assert response.deliveries[0].items[0].pounds == 125