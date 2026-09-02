from app.importers.historical_workbook import (
    calculate_row_fingerprint,
    validate_raw_row,
)


def test_valid_historical_row_has_no_issues() -> None:
    raw_data = {
        "B": "2025-01-02",
        "C": "Community Food Pantry",
        "F": "Van",
        "P": 100,
        "R": "source-123",
    }

    assert validate_raw_row(raw_data) == []


def test_historical_row_reports_missing_fields() -> None:
    raw_data = {
        "B": "2025-01-02",
        "C": None,
        "F": None,
        "P": None,
        "R": None,
    }

    assert validate_raw_row(raw_data) == [
        "missing food recipient",
        "missing vehicle",
        "missing recorded total pounds",
        "missing source record id",
    ]


def test_row_fingerprint_is_deterministic() -> None:
    first_row = {
        "B": "2025-01-02",
        "C": "Community Food Pantry",
    }
    same_row_different_order = {
        "C": "Community Food Pantry",
        "B": "2025-01-02",
    }

    assert calculate_row_fingerprint(first_row) == calculate_row_fingerprint(
        same_row_different_order
    )
