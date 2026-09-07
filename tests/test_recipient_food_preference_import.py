import csv
from pathlib import Path

import pytest

from app.importers.import_recipient_food_preferences import (
    REQUIRED_COLUMNS,
    category_codes_for_food,
    load_preference_rows,
)


def write_mapping(
    file_path: Path,
    rows: list[dict[str, str]],
) -> None:
    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=REQUIRED_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_anything_accepts_all_categories() -> None:
    all_codes = {
        "produce",
        "bread",
        "meat",
    }

    result = category_codes_for_food(
        accepted_food="Anything, small qty",
        all_category_codes=all_codes,
    )

    assert result == all_codes


@pytest.mark.parametrize(
    ("accepted_food", "expected"),
    [
        (
            "Produce and bread",
            {"produce", "bread"},
        ),
        (
            "Bread and prepared food, small qty",
            {"bread", "prepared_food"},
        ),
        (
            "Fresh Fruit and Veggies",
            {"produce"},
        ),
    ],
)
def test_specific_food_categories(
    accepted_food: str,
    expected: set[str],
) -> None:
    result = category_codes_for_food(
        accepted_food=accepted_food,
        all_category_codes={
            "produce",
            "bread",
            "prepared_food",
        },
    )

    assert result == expected


def test_operational_text_is_not_guessed() -> None:
    result = category_codes_for_food(
        accepted_food="Large Quantity Offload",
        all_category_codes={
            "produce",
            "bread",
        },
    )

    assert result == set()


def test_load_preference_rows_ignores_exclusions(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "mapping.csv"

    write_mapping(
        file_path,
        [
            {
                "source_name": "Unity Shoppe",
                "accepted_food": "Produce",
                "approved_decision": "merge",
                "approved_canonical_name": ("Unity Shoppe - SB"),
            },
            {
                "source_name": "Ford Van",
                "accepted_food": "",
                "approved_decision": "exclude",
                "approved_canonical_name": "",
            },
        ],
    )

    rows = load_preference_rows(file_path)

    assert len(rows) == 1
    assert rows[0].canonical_name == "Unity Shoppe - SB"
    assert rows[0].accepted_food == "Produce"
