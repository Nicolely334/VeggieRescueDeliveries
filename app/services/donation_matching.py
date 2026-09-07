from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

QuantityFit = Literal[
    "capacity_unknown",
    "full_offer_fits",
    "partial_offer_fits",
]


@dataclass(frozen=True)
class DonationFoodMatch:
    food_category_code: str
    offered_pounds: Decimal
    maximum_pounds: Decimal | None
    potential_pounds: Decimal | None
    quantity_fit: QuantityFit


def match_donation_food(
    offered_pounds_by_category: Mapping[str, Decimal],
    maximum_pounds_by_category: Mapping[str, Decimal | None],
) -> list[DonationFoodMatch]:
    matching_category_codes = offered_pounds_by_category.keys() & maximum_pounds_by_category.keys()

    matches: list[DonationFoodMatch] = []

    for category_code in sorted(matching_category_codes):
        offered_pounds = offered_pounds_by_category[category_code]
        maximum_pounds = maximum_pounds_by_category[category_code]

        if maximum_pounds is None:
            potential_pounds = None
            quantity_fit: QuantityFit = "capacity_unknown"
        elif offered_pounds <= maximum_pounds:
            potential_pounds = offered_pounds
            quantity_fit = "full_offer_fits"
        else:
            potential_pounds = maximum_pounds
            quantity_fit = "partial_offer_fits"

        matches.append(
            DonationFoodMatch(
                food_category_code=category_code,
                offered_pounds=offered_pounds,
                maximum_pounds=maximum_pounds,
                potential_pounds=potential_pounds,
                quantity_fit=quantity_fit,
            )
        )

    return matches
