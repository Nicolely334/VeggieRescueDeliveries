from app.importers.review_historical_rows import (
    calculate_business_signature,
    find_row_issues,
)


def valid_raw_data() -> dict[str, object]:
    return {
        "B": "2025-01-02",
        "C": "Community Food Pantry",
        "D": "Santa Barbara/Goleta",
        "E": "Kevin",
        "F": "Van",
        "G": 80,
        "H": 20,
        "I": None,
        "J": None,
        "K": None,
        "L": None,
        "M": None,
        "N": None,
        "O": None,
        "P": 100,
    }


def test_valid_row_has_no_review_issues() -> None:
    issues = find_row_issues(
        raw_data=valid_raw_data(),
        existing_issues=[],
        is_possible_duplicate=False,
    )

    assert issues == []


def test_vehicle_name_in_recipient_is_flagged() -> None:
    raw_data = valid_raw_data()
    raw_data["C"] = "Ford Van"

    issues = find_row_issues(
        raw_data=raw_data,
        existing_issues=[],
        is_possible_duplicate=False,
    )

    assert "recipient field contains a vehicle name" in issues


def test_incorrect_total_is_flagged() -> None:
    raw_data = valid_raw_data()
    raw_data["P"] = 90

    issues = find_row_issues(
        raw_data=raw_data,
        existing_issues=[],
        is_possible_duplicate=False,
    )

    assert any(
        issue.startswith("food amount sum")
        for issue in issues
    )


def test_legacy_food_column_is_flagged() -> None:
    raw_data = valid_raw_data()
    raw_data["I"] = 25
    raw_data["P"] = 125

    issues = find_row_issues(
        raw_data=raw_data,
        existing_issues=[],
        is_possible_duplicate=False,
    )

    assert (
        "unlabeled legacy column I contains weight"
        in issues
    )


def test_duplicate_delivery_is_flagged() -> None:
    issues = find_row_issues(
        raw_data=valid_raw_data(),
        existing_issues=[],
        is_possible_duplicate=True,
    )

    assert "possible duplicate delivery" in issues


def test_business_signature_ignores_source_id() -> None:
    first_row = valid_raw_data()
    first_row["R"] = "source-one"

    second_row = valid_raw_data()
    second_row["R"] = "source-two"

    assert calculate_business_signature(
        first_row
    ) == calculate_business_signature(
        second_row
    )