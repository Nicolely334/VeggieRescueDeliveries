import uuid

import pytest
from pydantic import ValidationError

from app.schemas.donation_allocation import DonationAllocationCreate


def build_allocation_data(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "recommendation_run_id": uuid.uuid4(),
        "recipient_site_id": uuid.uuid4(),
        "is_override": False,
        "items": [
            {
                "food_category_code": " Produce ",
                "pounds": 50.0,
            }
        ],
    }
    data.update(changes)
    return data


def test_allocation_create_normalizes_input() -> None:
    allocation = DonationAllocationCreate.model_validate(
        build_allocation_data(
            driver_name="  Taylor  ",
            notes="  Call before arrival  ",
        )
    )

    assert allocation.items[0].food_category_code == "produce"
    assert allocation.driver_name == "Taylor"
    assert allocation.notes == "Call before arrival"


def test_override_requires_reason() -> None:
    with pytest.raises(
        ValidationError,
        match="override_reason is required",
    ):
        DonationAllocationCreate.model_validate(
            build_allocation_data(is_override=True)
        )


def test_reason_requires_override() -> None:
    with pytest.raises(
        ValidationError,
        match="override_reason requires is_override",
    ):
        DonationAllocationCreate.model_validate(
            build_allocation_data(
                override_reason="Urgent need",
            )
        )


def test_duplicate_food_categories_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="food categories cannot be repeated",
    ):
        DonationAllocationCreate.model_validate(
            build_allocation_data(
                items=[
                    {
                        "food_category_code": "produce",
                        "pounds": 25.0,
                    },
                    {
                        "food_category_code": "PRODUCE",
                        "pounds": 25.0,
                    },
                ]
            )
        )


def test_pounds_cannot_exceed_database_precision() -> None:
    with pytest.raises(ValidationError, match="multiple of 0.01"):
        DonationAllocationCreate.model_validate(
            build_allocation_data(
                items=[
                    {
                        "food_category_code": "produce",
                        "pounds": 1.001,
                    }
                ]
            )
        )
