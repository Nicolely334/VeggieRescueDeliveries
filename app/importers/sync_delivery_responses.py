import argparse
import csv
import json
import uuid
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.importers.historical_workbook import (
    ParsedRow,
    build_summary,
    calculate_row_fingerprint,
    is_blank,
    stage_rows,
    validate_raw_row,
)
from app.importers.import_recipient_mapping import (
    DEFAULT_SOURCE_SYSTEM,
    normalize_name,
)
from app.importers.promote_historical_deliveries import (
    additional_row_issues,
    promote_batch,
)
from app.importers.review_historical_rows import (
    calculate_business_signature,
    decimal_value,
    find_row_issues,
)
from app.models.delivery import Delivery
from app.models.import_batch import ImportBatch
from app.models.recipient_alias import RecipientAlias

SOURCE_COLUMN_COUNT = 18
SOURCE_COLUMNS = tuple(chr(ord("A") + index) for index in range(SOURCE_COLUMN_COUNT))

EXPECTED_HEADERS = {
    1: "Delivery Date",
    2: "Food Recipient",
    3: "Food Recipient Location",
    4: "VR Driver",
    5: "Vehicle",
    6: "Food Deliveries >> Produce >> Pounds",
    7: "Food Deliveries >> Packaged >> Pounds",
}

DELIVERY_DATE_FORMATS = (
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
)


def find_existing_batch_id(
    database: Session,
    file_sha256: str,
) -> str | None:
    batch_id = database.scalar(
        select(ImportBatch.id).where(
            ImportBatch.file_sha256 == file_sha256
        )
    )

    if batch_id is None:
        return None

    return str(batch_id)

def validate_header(header: list[str]) -> None:
    if len(header) != SOURCE_COLUMN_COUNT:
        raise ValueError(
            f"expected {SOURCE_COLUMN_COUNT} columns, found {len(header)}"
        )

    for column_index, expected_header in EXPECTED_HEADERS.items():
        actual_header = header[column_index].strip()

        if actual_header != expected_header:
            column = SOURCE_COLUMNS[column_index]
            raise ValueError(
                f"column {column} must be {expected_header!r}, "
                f"found {actual_header!r}"
            )


def normalize_delivery_date(value: str) -> str:
    for date_format in DELIVERY_DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue

    raise ValueError(f"invalid delivery date: {value}")


def parse_tsv(file_path: Path) -> list[ParsedRow]:
    parsed_rows: list[ParsedRow] = []

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.reader(
            source_file,
            delimiter="\t",
        )
        header = next(reader, None)

        if header is None:
            raise ValueError("TSV file is empty")

        validate_header(header)

        for row_number, values in enumerate(reader, start=2):
            if not values or all(not value.strip() for value in values):
                continue

            if len(values) != SOURCE_COLUMN_COUNT:
                raise ValueError(
                    f"line {row_number}: expected "
                    f"{SOURCE_COLUMN_COUNT} columns, found {len(values)}"
                )

            raw_data: dict[str, object] = {
                column: value.strip() or None
                for column, value in zip(
                    SOURCE_COLUMNS,
                    values,
                    strict=True,
                )
            }

            validation_issues = validate_raw_row(raw_data)
            raw_delivery_date = raw_data.get("B")

            if not is_blank(raw_delivery_date):
                try:
                    raw_data["B"] = normalize_delivery_date(
                        str(raw_delivery_date)
                    )
                except ValueError:
                    validation_issues.append("delivery date is invalid")

            raw_source_id = raw_data.get("R")
            source_record_id = (
                None
                if is_blank(raw_source_id)
                else str(raw_source_id).strip()
            )

            parsed_rows.append(
                ParsedRow(
                    row_number=row_number,
                    source_record_id=source_record_id,
                    row_fingerprint=calculate_row_fingerprint(raw_data),
                    raw_data=raw_data,
                    validation_issues=list(
                        dict.fromkeys(validation_issues)
                    ),
                )
            )

    return parsed_rows


def load_database_context(
    database: Session,
    source_system: str,
) -> tuple[set[str], dict[str, RecipientAlias]]:
    source_ids = database.scalars(
        select(Delivery.source_record_id).where(
            Delivery.source_system == source_system,
            Delivery.source_record_id.is_not(None),
        )
    ).all()

    existing_source_ids = {
        source_id
        for source_id in source_ids
        if source_id is not None
    }

    aliases = database.scalars(
        select(RecipientAlias).where(
            RecipientAlias.source_system == source_system
        )
    ).all()

    aliases_by_name = {
        alias.normalized_name: alias
        for alias in aliases
    }

    return existing_source_ids, aliases_by_name


def build_database_comparison(
    parsed_rows: list[ParsedRow],
    existing_source_ids: set[str],
    aliases_by_name: dict[str, RecipientAlias],
) -> dict[str, object]:
    signature_counts = Counter(
        calculate_business_signature(row.raw_data)
        for row in parsed_rows
    )
    source_id_counts = Counter(
        row.source_record_id
        for row in parsed_rows
        if row.source_record_id is not None
    )

    already_imported_rows = 0
    new_rows = 0
    review_rows = 0
    new_total_pounds = Decimal("0")
    issue_counts: Counter[str] = Counter()

    for row in parsed_rows:
        source_record_id = row.source_record_id

        if (
            source_record_id is not None
            and source_record_id in existing_source_ids
        ):
            already_imported_rows += 1
            continue

        recipient_name = str(
            row.raw_data.get("C") or ""
        ).strip()
        alias = aliases_by_name.get(
            normalize_name(recipient_name)
        )

        signature = calculate_business_signature(row.raw_data)
        issues = find_row_issues(
            raw_data=row.raw_data,
            existing_issues=row.validation_issues,
            is_possible_duplicate=(
                signature_counts[signature] > 1
            ),
        )
        issues.extend(
            additional_row_issues(
                raw_data=row.raw_data,
                alias=alias,
            )
        )

        if (
            source_record_id is not None
            and source_id_counts[source_record_id] > 1
        ):
            issues.append("duplicate source record id")

        issues = list(dict.fromkeys(issues))

        if issues:
            review_rows += 1
            issue_counts.update(issues)
            continue

        total_pounds = decimal_value(
            row.raw_data.get("P")
        )

        if total_pounds is None:
            raise RuntimeError(
                f"total parsing failed for row {row.row_number}"
            )

        new_rows += 1
        new_total_pounds += total_pounds

    return {
        "database_already_imported_rows": already_imported_rows,
        "database_new_rows": new_rows,
        "database_review_rows": review_rows,
        "database_new_total_pounds": str(new_total_pounds),
        "database_issue_counts": dict(
            sorted(issue_counts.items())
        ),
    }

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a delivery-response TSV with the database "
            "and optionally import validated new deliveries."
        )
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the Google Sheets TSV export.",
    )
    parser.add_argument(
        "--source-system",
        default=DEFAULT_SOURCE_SYSTEM,
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help=(
            "Stage the source rows and import only validated "
            "deliveries that are not already in the database."
        ),
    )
    arguments = parser.parse_args()
    file_path = arguments.file.resolve()

    if not file_path.is_file():
        parser.error(f"file does not exist: {file_path}")

    parsed_rows = parse_tsv(file_path)
    summary = build_summary(
        file_path,
        parsed_rows,
    )

    with SessionLocal() as database:
        existing_source_ids, aliases_by_name = (
            load_database_context(
                database,
                arguments.source_system,
            )
        )

        comparison = build_database_comparison(
            parsed_rows=parsed_rows,
            existing_source_ids=existing_source_ids,
            aliases_by_name=aliases_by_name,
        )

    summary.update(comparison)
    summary["source_format"] = "tsv"
    summary["source_system"] = arguments.source_system
    summary["committed"] = False

    if arguments.commit:
        new_rows = comparison["database_new_rows"]

        if not isinstance(new_rows, int):
            raise RuntimeError("database_new_rows must be an integer")

        if new_rows == 0:
            summary["no_op"] = True
            summary["message"] = (
                "No validated new deliveries to import."
            )
        else:
            with SessionLocal() as database:
                existing_batch_id = find_existing_batch_id(
                    database=database,
                    file_sha256=str(summary["file_sha256"]),
                )

            if existing_batch_id is None:
                batch_id = stage_rows(
                    file_path=file_path,
                    parsed_rows=parsed_rows,
                    summary=summary,
                )
                reused_batch = False
            else:
                batch_id = existing_batch_id
                reused_batch = True

            try:
                with SessionLocal() as database:
                    promotion_summary = promote_batch(
                        db=database,
                        batch_id=uuid.UUID(batch_id),
                        source_system=arguments.source_system,
                        commit=True,
                    )
            except Exception as error:
                raise RuntimeError(
                    f"batch {batch_id} was staged, "
                    "but promotion failed"
                ) from error

            summary["batch_id"] = batch_id
            summary["reused_batch"] = reused_batch
            summary["promotion"] = promotion_summary
            summary["committed"] = True
            summary["no_op"] = False

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

if __name__ == "__main__":
    main()