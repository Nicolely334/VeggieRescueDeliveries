import csv
from pathlib import Path

import pytest

from app.importers.import_recipient_mapping import (
    REQUIRED_COLUMNS,
    load_mapping_rows,
    normalize_name,
)


def write_mapping(
    file_path: Path,
    rows: list[dict[str, str]],
) -> None:
    with file_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=REQUIRED_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_normalize_name() -> None:
    assert normalize_name("  UNITY   Shoppe  ") == "unity shoppe"


def test_load_mapping_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "mapping.csv"

    write_mapping(
        file_path,
        [
            {
                "source_name": "Unity Shoppe",
                "approved_decision": "merge",
                "approved_canonical_name": "Unity Shoppe - SB",
                "approved_priority": "2",
                "approved_is_fallback": "FALSE",
                "approved_is_active": "TRUE",
                "review_notes": "Legacy label",
            },
            {
                "source_name": "14 foot truck",
                "approved_decision": "exclude",
                "approved_canonical_name": "",
                "approved_priority": "",
                "approved_is_fallback": "",
                "approved_is_active": "",
                "review_notes": "Vehicle label",
            },
        ],
    )

    rows = load_mapping_rows(file_path)

    assert len(rows) == 2
    assert rows[0].canonical_name == "Unity Shoppe - SB"
    assert rows[0].priority == 2
    assert rows[1].decision == "exclude"
    assert rows[1].canonical_name is None


def test_mapping_requires_canonical_name(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "mapping.csv"

    write_mapping(
        file_path,
        [
            {
                "source_name": "Example recipient",
                "approved_decision": "include",
                "approved_canonical_name": "",
                "approved_priority": "3",
                "approved_is_fallback": "FALSE",
                "approved_is_active": "TRUE",
                "review_notes": "",
            }
        ],
    )

    with pytest.raises(
        ValueError,
        match="approved_canonical_name",
    ):
        load_mapping_rows(file_path)


def test_mapping_rejects_invalid_priority(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "mapping.csv"

    write_mapping(
        file_path,
        [
            {
                "source_name": "Example recipient",
                "approved_decision": "include",
                "approved_canonical_name": "Example recipient",
                "approved_priority": "6",
                "approved_is_fallback": "FALSE",
                "approved_is_active": "TRUE",
                "review_notes": "",
            }
        ],
    )

    with pytest.raises(
        ValueError,
        match="approved_priority",
    ):
        load_mapping_rows(file_path)
