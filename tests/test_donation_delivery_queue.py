from app.main import app
from app.schemas.donation_delivery_queue import (
    DonationQueueFoodMatchRead,
)


def test_donation_delivery_queue_route_is_registered() -> None:
    paths = app.openapi()["paths"]

    path = "/api/v1/donation-offers/{offer_id}/delivery-queue"

    assert "get" in paths[path]


def test_food_match_response_allows_unknown_capacity() -> None:
    match = DonationQueueFoodMatchRead(
        food_category_code="produce",
        category_name="Produce",
        offered_pounds=100,
        maximum_pounds=None,
        potential_pounds=None,
        quantity_fit="capacity_unknown",
    )

    assert match.maximum_pounds is None
    assert match.potential_pounds is None
    assert match.quantity_fit == "capacity_unknown"
