import pytest
from pydantic import ValidationError

from app.schemas.food_preference import (
    RecipientFoodPreferenceInput,
    RecipientFoodPreferencesReplace,
)


def test_food_preference_accepts_valid_data() -> None:
    preference = RecipientFoodPreferenceInput(
        food_category_code=" Produce ",
        maximum_pounds=150,
        notes="  Refrigerated storage available  ",
    )

    assert preference.food_category_code == "produce"
    assert preference.maximum_pounds == 150
    assert preference.notes == "Refrigerated storage available"


def test_food_preference_converts_blank_notes_to_none() -> None:
    preference = RecipientFoodPreferenceInput(
        food_category_code="bread",
        notes="   ",
    )

    assert preference.notes is None


def test_food_preference_rejects_nonpositive_capacity() -> None:
    with pytest.raises(ValidationError):
        RecipientFoodPreferenceInput(
            food_category_code="produce",
            maximum_pounds=0,
        )


def test_food_preferences_reject_duplicate_categories() -> None:
    with pytest.raises(ValidationError):
        RecipientFoodPreferencesReplace(
            items=[
                {
                    "food_category_code": "produce",
                },
                {
                    "food_category_code": "PRODUCE",
                },
            ]
        )


def test_food_preferences_allow_empty_replacement() -> None:
    preferences = RecipientFoodPreferencesReplace(items=[])

    assert preferences.items == []
