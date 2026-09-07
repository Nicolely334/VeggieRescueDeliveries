from decimal import Decimal

from app.services.donation_matching import (
    DonationFoodMatch,
    match_donation_food,
)


def test_recipient_without_matching_category_is_ineligible() -> None:
    matches = match_donation_food(
        offered_pounds_by_category={
            "produce": Decimal("100.00"),
        },
        maximum_pounds_by_category={
            "bread": Decimal("25.00"),
        },
    )

    assert matches == []


def test_unknown_capacity_is_not_treated_as_unlimited() -> None:
    matches = match_donation_food(
        offered_pounds_by_category={
            "produce": Decimal("100.00"),
        },
        maximum_pounds_by_category={
            "produce": None,
        },
    )

    assert matches == [
        DonationFoodMatch(
            food_category_code="produce",
            offered_pounds=Decimal("100.00"),
            maximum_pounds=None,
            potential_pounds=None,
            quantity_fit="capacity_unknown",
        )
    ]


def test_full_offer_fits_within_known_capacity() -> None:
    matches = match_donation_food(
        offered_pounds_by_category={
            "produce": Decimal("100.00"),
        },
        maximum_pounds_by_category={
            "produce": Decimal("150.00"),
        },
    )

    assert matches[0].potential_pounds == Decimal("100.00")
    assert matches[0].quantity_fit == "full_offer_fits"


def test_offer_is_capped_at_recipient_capacity() -> None:
    matches = match_donation_food(
        offered_pounds_by_category={
            "produce": Decimal("100.00"),
        },
        maximum_pounds_by_category={
            "produce": Decimal("40.00"),
        },
    )

    assert matches[0].potential_pounds == Decimal("40.00")
    assert matches[0].quantity_fit == "partial_offer_fits"


def test_matches_are_sorted_by_food_category() -> None:
    matches = match_donation_food(
        offered_pounds_by_category={
            "produce": Decimal("100.00"),
            "bread": Decimal("30.00"),
            "dairy": Decimal("20.00"),
        },
        maximum_pounds_by_category={
            "produce": Decimal("50.00"),
            "bread": None,
            "other": Decimal("10.00"),
        },
    )

    assert [
        match.food_category_code
        for match in matches
    ] == [
        "bread",
        "produce",
    ]