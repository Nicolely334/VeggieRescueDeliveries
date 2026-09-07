from datetime import date
from decimal import Decimal

import pytest

from app.importers.promote_historical_deliveries import (
    build_item_weights,
    parse_delivery_date,
)


def empty_food_data() -> dict[str, object]:
    return {column: None for column in "GHIJKLMNO"}


def test_parse_delivery_datetime() -> None:
    result = parse_delivery_date("2025-06-01T00:00:00")

    assert result == date(2025, 6, 1)


def test_build_items_uses_confirmed_categories() -> None:
    raw_data = empty_food_data()
    raw_data["I"] = 25
    raw_data["N"] = 5

    assert build_item_weights(raw_data) == {
        "dairy": Decimal("25"),
        "other": Decimal("5"),
    }


def test_build_items_omits_blank_and_zero_values() -> None:
    raw_data = empty_food_data()
    raw_data["G"] = 80
    raw_data["H"] = 0

    assert build_item_weights(raw_data) == {
        "produce": Decimal("80"),
    }


def test_build_items_rejects_negative_weight() -> None:
    raw_data = empty_food_data()
    raw_data["G"] = -5

    with pytest.raises(
        ValueError,
        match="negative weight",
    ):
        build_item_weights(raw_data)
