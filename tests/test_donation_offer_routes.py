import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.api.routes.donation_offers import (
    build_offer_read,
)
from app.main import app
from app.models.donation_offer import DonationOffer
from app.models.donation_offer_item import (
    DonationOfferItem,
)


def test_farm_and_offer_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "get" in paths["/api/v1/farms"]
    assert "post" in paths["/api/v1/farms"]

    assert "get" in paths["/api/v1/donation-offers"]
    assert "post" in paths["/api/v1/donation-offers"]

    assert "get" in paths["/api/v1/donation-offers/{offer_id}"]


def test_build_offer_read_calculates_total() -> None:
    now = datetime.now(UTC)
    farm_id = uuid.uuid4()
    offer_id = uuid.uuid4()

    offer = DonationOffer(
        id=offer_id,
        farm_id=farm_id,
        status="open",
        available_from=now,
        pickup_by=now,
        notes="Test offer",
        created_at=now,
        updated_at=now,
    )

    produce = DonationOfferItem(
        id=uuid.uuid4(),
        donation_offer_id=offer_id,
        food_category_code="produce",
        pounds=Decimal("125.50"),
        created_at=now,
    )
    bread = DonationOfferItem(
        id=uuid.uuid4(),
        donation_offer_id=offer_id,
        food_category_code="bread",
        pounds=Decimal("40.00"),
        created_at=now,
    )

    response = build_offer_read(
        offer=offer,
        farm_name="Sunrise Farm",
        item_rows=[
            (produce, "Produce"),
            (bread, "Bread"),
        ],
    )

    assert response.farm_name == "Sunrise Farm"
    assert response.status == "open"
    assert response.total_pounds == 165.5
    assert len(response.items) == 2
    assert response.items[0].pounds == 125.5
