import argparse
import csv
import json
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.import_row import ImportRow

FOOD_COLUMNS = ("G", "H", "I", "J", "K", "L", "M", "N", "O")
LEGACY_COLUMNS = ("I", "N")
BUSINESS_COLUMNS = tuple(
    chr(column_number)
    for column_number in range(ord("B"), ord("P") + 1)
)
VEHICLE_RECIPIENTS = {
    "14 foot truck",
    "14 ft truck",
    "ford van",
    "new van",
    "van",
}


def is_blank(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and not value.strip()
    )


def decimal_value(value: object) -> Decimal | None:
    if is_blank(value):
        return Decimal("0")

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def calculate_business_signature(
    raw_data: dict[str, object],
) -> str:
    business_data = {
        column: raw_data.get(column)
        for column in BUSINESS_COLUMNS
    }

    return json.dumps(
        business_data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def find_row_issues(
    raw_data: dict[str, object],
    existing_issues: list[str],
    is_possible_duplicate: bool,
) -> list[str]:
    issues = list(existing_issues)

    recipient = str(raw_data.get("C") or "").strip()
    recipient_lower = recipient.lower()

    if recipient_lower in VEHICLE_RECIPIENTS:
        issues.append("recipient field contains a vehicle name")

    if recipient_lower == "other/not listed":
        issues.append("recipient requires manual identification")

    for column in LEGACY_COLUMNS:
        value = decimal_value(raw_data.get(column))

        if value is None:
            issues.append(
                f"legacy column {column} contains a nonnumeric value"
            )
        elif value != 0:
            issues.append(
                f"unlabeled legacy column {column} contains weight"
            )

    food_total = Decimal("0")
    food_values_are_valid = True

    for column in FOOD_COLUMNS:
        value = decimal_value(raw_data.get(column))

        if value is None:
            issues.append(
                f"food column {column} contains a nonnumeric value"
            )
            food_values_are_valid = False
        else:
            food_total += value

    recorded_total_raw = raw_data.get("P")

    if not is_blank(recorded_total_raw):
        recorded_total = decimal_value(recorded_total_raw)

        if recorded_total is None:
            issues.append("recorded total is not numeric")
        elif (
            food_values_are_valid
            and abs(food_total - recorded_total)
            > Decimal("0.01")
        ):
            issues.append(
                "food amount sum "
                f"{food_total} does not match recorded total "
                f"{recorded_total}"
            )

    location = str(raw_data.get("D") or "")

    if "los angelos" in location.lower():
        issues.append("location spelling needs review")

    if "\n" in location:
        issues.append("multiple locations stored in one cell")

    if is_possible_duplicate:
        issues.append("possible duplicate delivery")

    return list(dict.fromkeys(issues))


def write_review_report(
    rows: list[ImportRow],
    output_path: Path,
) -> dict[str, object]:
    signature_counts = Counter(
        calculate_business_signature(row.raw_data)
        for row in rows
    )
    issue_counts: Counter[str] = Counter()
    report_rows = []

    for row in rows:
        signature = calculate_business_signature(
            row.raw_data
        )
        issues = find_row_issues(
            raw_data=row.raw_data,
            existing_issues=row.validation_issues,
            is_possible_duplicate=(
                signature_counts[signature] > 1
            ),
        )

        if not issues:
            continue

        issue_counts.update(issues)

        report_rows.append(
            {
                "database_row_id": str(row.id),
                "source_row_number": row.row_number,
                "source_record_id": (
                    row.source_record_id or ""
                ),
                "delivery_date": row.raw_data.get("B") or "",
                "food_recipient": row.raw_data.get("C") or "",
                "recipient_location": (
                    row.raw_data.get("D") or ""
                ),
                "driver": row.raw_data.get("E") or "",
                "vehicle": row.raw_data.get("F") or "",
                "recorded_total_pounds": (
                    row.raw_data.get("P") or ""
                ),
                "issues": " | ".join(issues),
            }
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "database_row_id",
        "source_row_number",
        "source_record_id",
        "delivery_date",
        "food_recipient",
        "recipient_location",
        "driver",
        "vehicle",
        "recorded_total_pounds",
        "issues",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as report_file:
        writer = csv.DictWriter(
            report_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(report_rows)

    return {
        "total_staged_rows": len(rows),
        "review_rows": len(report_rows),
        "clean_candidate_rows": len(rows) - len(report_rows),
        "issue_counts": dict(sorted(issue_counts.items())),
        "report": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review staged historical delivery rows."
    )
    parser.add_argument(
        "--batch-id",
        required=True,
        type=uuid.UUID,
        help="Import batch UUID to review.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/reports/historical_import_review.csv"
        ),
        help="Destination for the CSV review report.",
    )

    arguments = parser.parse_args()

    with SessionLocal() as database:
        batch = database.get(
            ImportBatch,
            arguments.batch_id,
        )

        if batch is None:
            parser.error(
                f"batch not found: {arguments.batch_id}"
            )

        rows = list(
            database.scalars(
                select(ImportRow)
                .where(
                    ImportRow.batch_id
                    == arguments.batch_id
                )
                .order_by(ImportRow.row_number)
            )
        )

    summary = write_review_report(
        rows,
        arguments.output.resolve(),
    )
    summary["batch_id"] = str(arguments.batch_id)
    summary["file"] = batch.file_name

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()