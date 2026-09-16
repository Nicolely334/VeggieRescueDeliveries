import csv
import uuid
from pathlib import Path

from app.importers.historical_workbook import (
    ParsedRow,
    calculate_row_fingerprint,
    validate_raw_row,
)
from app.importers.sync_delivery_responses import (
    SOURCE_COLUMNS,
    build_database_comparison,
    normalize_delivery_date,
    parse_tsv,
)
from app.models.recipient_alias import RecipientAlias

HEADERS = [
    "",
    "Delivery Date",
    "Food Recipient",
    "Food Recipient Location",
    "VR Driver",
    "Vehicle",
    "Food Deliveries >> Produce >> Pounds",
    "Food Deliveries >> Packaged >> Pounds",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
]


def valid_raw_data(
    delivery_date: str,
    source_record_id: str | None,
    recipient: str = "Community Food Pantry",
) -> dict[str, object]:
    raw_data: dict[str, object] = {
        column: None
        for column in SOURCE_COLUMNS
    }
    raw_data.update(
        {
            "A": "1001",
            "B": delivery_date,
            "C": recipient,
            "D": "Santa Barbara/Goleta",
            "E": "Kevin",
            "F": "Van",
            "G": "100",
            "P": "100",
            "R": source_record_id,
        }
    )
    return raw_data


def parsed_row(
    row_number: int,
    delivery_date: str,
    source_record_id: str | None,
    recipient: str = "Community Food Pantry",
) -> ParsedRow:
    raw_data = valid_raw_data(
        delivery_date=delivery_date,
        source_record_id=source_record_id,
        recipient=recipient,
    )

    return ParsedRow(
        row_number=row_number,
        source_record_id=source_record_id,
        row_fingerprint=calculate_row_fingerprint(raw_data),
        raw_data=raw_data,
        validation_issues=validate_raw_row(raw_data),
    )


def included_alias(
    recipient: str = "Community Food Pantry",
) -> RecipientAlias:
    return RecipientAlias(
        source_system="google_sheets_delivery_master",
        source_name=recipient,
        normalized_name=recipient.casefold(),
        decision="include",
        recipient_site_id=uuid.uuid4(),
    )


def test_normalize_delivery_date() -> None:
    assert normalize_delivery_date("09-13-2026") == "2026-09-13"
    assert normalize_delivery_date("2026-09-13") == "2026-09-13"


def test_parse_tsv_maps_all_source_columns(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "deliveries.tsv"
    raw_data = valid_raw_data(
        delivery_date="09-13-2026",
        source_record_id="1234567890123456789",
    )

    with file_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output:
        writer = csv.writer(
            output,
            delimiter="\t",
        )
        writer.writerow(HEADERS)
        writer.writerow(
            [
                raw_data[column] or ""
                for column in SOURCE_COLUMNS
            ]
        )

    rows = parse_tsv(file_path)

    assert len(rows) == 1
    assert rows[0].raw_data["B"] == "2026-09-13"
    assert rows[0].raw_data["G"] == "100"
    assert rows[0].raw_data["P"] == "100"
    assert rows[0].source_record_id == "1234567890123456789"
    assert rows[0].validation_issues == []


def test_database_comparison_separates_rows() -> None:
    rows = [
        parsed_row(
            row_number=2,
            delivery_date="2026-09-10",
            source_record_id="existing-source",
        ),
        parsed_row(
            row_number=3,
            delivery_date="2026-09-11",
            source_record_id="new-source",
        ),
        parsed_row(
            row_number=4,
            delivery_date="2026-09-12",
            source_record_id=None,
        ),
    ]
    alias = included_alias()

    summary = build_database_comparison(
        parsed_rows=rows,
        existing_source_ids={"existing-source"},
        aliases_by_name={
            alias.normalized_name: alias,
        },
    )

    assert summary["database_already_imported_rows"] == 1
    assert summary["database_new_rows"] == 1
    assert summary["database_review_rows"] == 1
    assert summary["database_new_total_pounds"] == "100"
    assert summary["database_issue_counts"] == {
        "missing source record id": 1,
    }


def test_database_comparison_blocks_unknown_recipient() -> None:
    rows = [
        parsed_row(
            row_number=2,
            delivery_date="2026-09-13",
            source_record_id="new-source",
            recipient="Unknown Recipient",
        )
    ]

    summary = build_database_comparison(
        parsed_rows=rows,
        existing_source_ids=set(),
        aliases_by_name={},
    )

    assert summary["database_new_rows"] == 0
    assert summary["database_review_rows"] == 1
    assert summary["database_issue_counts"] == {
        "recipient alias not found": 1,
    }