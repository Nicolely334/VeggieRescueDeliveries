import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.api.routes.recipient_food_preferences import (
    build_preferences_read,
)
from app.main import app
from app.models.recipient_food_preference import (
    RecipientFoodPreference,
)
from app.models.recipient_site import RecipientSite


def test_food_preference_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "get" in paths["/api/v1/food-categories"]

    preference_path = "/api/v1/recipient-sites/{recipient_site_id}/food-preferences"

    assert "get" in paths[preference_path]
    assert "put" in paths[preference_path]


def test_build_preferences_read() -> None:
    now = datetime.now(UTC)
    recipient_id = uuid.uuid4()

    recipient = RecipientSite(
        id=recipient_id,
        name="Community Food Pantry",
        priority=1,
        is_active=True,
        is_fallback=False,
        created_at=now,
        updated_at=now,
    )

    preference = RecipientFoodPreference(
        id=uuid.uuid4(),
        recipient_site_id=recipient_id,
        food_category_code="produce",
        maximum_pounds=Decimal("150.00"),
        notes="Refrigerated storage available",
        created_at=now,
        updated_at=now,
    )

    response = build_preferences_read(
        recipient=recipient,
        preference_rows=[
            (preference, "Produce"),
        ],
    )

    assert response.recipient_site_id == recipient_id
    assert response.recipient_name == ("Community Food Pantry")
    assert len(response.preferences) == 1

    saved_preference = response.preferences[0]

    assert saved_preference.food_category_code == "produce"
    assert saved_preference.category_name == "Produce"
    assert saved_preference.maximum_pounds == 150
