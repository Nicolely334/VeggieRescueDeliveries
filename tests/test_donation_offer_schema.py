import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.donation_offer import DonationOfferCreate


def valid_offer_data() -> dict[str, object]:
    return {
        "farm_id": uuid.uuid4(),
        "available_from": datetime(
            2026,
            9,
            7,
            8,
            0,
            tzinfo=UTC,
        ),
        "pickup_by": datetime(
            2026,
            9,
            7,
            17,
            0,
            tzinfo=UTC,
        ),
        "notes": "  Keep refrigerated  ",
        "items": [
            {
                "food_category_code": " Produce ",
                "pounds": 125,
            },
            {
                "food_category_code": "bread",
                "pounds": 40,
            },
        ],
    }


def test_donation_offer_accepts_valid_data() -> None:
    offer = DonationOfferCreate.model_validate(valid_offer_data())

    assert offer.notes == "Keep refrigerated"
    assert len(offer.items) == 2
    assert offer.items[0].food_category_code == "produce"
    assert offer.items[0].pounds == 125


def test_donation_offer_requires_an_item() -> None:
    data = valid_offer_data()
    data["items"] = []

    with pytest.raises(ValidationError):
        DonationOfferCreate.model_validate(data)


def test_donation_offer_rejects_nonpositive_pounds() -> None:
    data = valid_offer_data()
    data["items"] = [
        {
            "food_category_code": "produce",
            "pounds": 0,
        }
    ]

    with pytest.raises(ValidationError):
        DonationOfferCreate.model_validate(data)


def test_donation_offer_rejects_invalid_pickup_window() -> None:
    data = valid_offer_data()
    data["pickup_by"] = datetime(
        2026,
        9,
        7,
        7,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(ValidationError):
        DonationOfferCreate.model_validate(data)


def test_donation_offer_rejects_duplicate_categories() -> None:
    data = valid_offer_data()
    data["items"] = [
        {
            "food_category_code": "produce",
            "pounds": 100,
        },
        {
            "food_category_code": "PRODUCE",
            "pounds": 50,
        },
    ]

    with pytest.raises(ValidationError):
        DonationOfferCreate.model_validate(data)


def test_donation_offer_requires_timezone() -> None:
    data = valid_offer_data()
    data["available_from"] = datetime(
        2026,
        9,
        7,
        8,
        0,
    )

    with pytest.raises(ValidationError):
        DonationOfferCreate.model_validate(data)
