import argparse
import csv
import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.import_row import ImportRow

VEHICLE_RECIPIENT_NAMES = {
    "14 foot truck",
    "14 ft truck",
    "ford van",
    "new van",
    "van",
}

FALLBACK_NAME_HINTS = (
    "farm",
    "goat",
    "sanctuary",
    "pork palace",
)


@dataclass
class RecipientSummary:
    source_name: str
    delivery_count: int = 0
    dates: set[str] = field(default_factory=set)
    locations: set[str] = field(default_factory=set)
    recorded_total_pounds: Decimal = Decimal("0")


def normalized_text(value: object) -> str:
    return str(value or "").strip()


def decimal_value(value: object) -> Decimal | None:
    if value is None or value == "":
        return None

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def suggest_mapping(
    source_name: str,
) -> tuple[str, str, str]:
    normalized_name = source_name.casefold()

    if normalized_name in VEHICLE_RECIPIENT_NAMES:
        return (
            "exclude",
            "",
            "recipient field appears to contain a vehicle name",
        )

    if normalized_name == "other/not listed":
        return (
            "review",
            "",
            "specific recipient must be identified",
        )

    if any(hint in normalized_name for hint in FALLBACK_NAME_HINTS):
        return (
            "review",
            source_name,
            "confirm whether this is a fallback destination",
        )

    return (
        "include",
        source_name,
        "",
    )


def build_recipient_summaries(
    raw_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    summaries: dict[str, RecipientSummary] = {}
    missing_recipient_rows = 0

    for raw_data in raw_rows:
        source_name = normalized_text(raw_data.get("C"))

        if not source_name:
            missing_recipient_rows += 1
            continue

        summary = summaries.setdefault(
            source_name,
            RecipientSummary(source_name=source_name),
        )
        summary.delivery_count += 1

        delivery_date = normalized_text(raw_data.get("B"))

        if delivery_date:
            summary.dates.add(delivery_date.split("T", 1)[0])

        location = normalized_text(raw_data.get("D"))

        if location:
            summary.locations.update(part.strip() for part in location.splitlines() if part.strip())

        recorded_total = decimal_value(raw_data.get("P"))

        if recorded_total is not None:
            summary.recorded_total_pounds += recorded_total

    output_rows = []

    for source_name in sorted(
        summaries,
        key=str.casefold,
    ):
        summary = summaries[source_name]

        (
            suggested_decision,
            suggested_canonical_name,
            review_reason,
        ) = suggest_mapping(source_name)

        output_rows.append(
            {
                "source_name": source_name,
                "delivery_count": summary.delivery_count,
                "first_delivery_date": (min(summary.dates) if summary.dates else ""),
                "last_delivery_date": (max(summary.dates) if summary.dates else ""),
                "observed_locations": " | ".join(sorted(summary.locations)),
                "recorded_total_pounds": format(
                    summary.recorded_total_pounds,
                    "f",
                ),
                "suggested_decision": suggested_decision,
                "suggested_canonical_name": (suggested_canonical_name),
                "review_reason": review_reason,
                "approved_decision": "",
                "approved_canonical_name": "",
                "approved_is_fallback": "",
                "notes": "",
            }
        )

    return output_rows, missing_recipient_rows


def write_mapping_report(
    output_rows: list[dict[str, object]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "source_name",
        "delivery_count",
        "first_delivery_date",
        "last_delivery_date",
        "observed_locations",
        "recorded_total_pounds",
        "suggested_decision",
        "suggested_canonical_name",
        "review_reason",
        "approved_decision",
        "approved_canonical_name",
        "approved_is_fallback",
        "notes",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(output_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a recipient mapping review file.")
    parser.add_argument(
        "--batch-id",
        required=True,
        type=uuid.UUID,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/recipient_mapping.csv"),
    )

    arguments = parser.parse_args()

    with SessionLocal() as database:
        batch = database.get(
            ImportBatch,
            arguments.batch_id,
        )

        if batch is None:
            parser.error(f"batch not found: {arguments.batch_id}")

        import_rows = list(
            database.scalars(
                select(ImportRow)
                .where(ImportRow.batch_id == arguments.batch_id)
                .order_by(ImportRow.row_number)
            )
        )

        file_name = batch.file_name

    mapping_rows, missing_recipient_rows = build_recipient_summaries(
        [row.raw_data for row in import_rows]
    )

    output_path = arguments.output.resolve()

    write_mapping_report(
        mapping_rows,
        output_path,
    )

    decision_counts = Counter(str(row["suggested_decision"]) for row in mapping_rows)

    print(
        json.dumps(
            {
                "batch_id": str(arguments.batch_id),
                "file": file_name,
                "source_labels": len(mapping_rows),
                "missing_recipient_rows": (missing_recipient_rows),
                "suggested_decisions": dict(sorted(decision_counts.items())),
                "report": str(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
