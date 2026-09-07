import argparse
import json
import uuid
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.importers.historical_workbook import validate_raw_row
from app.importers.import_recipient_mapping import (
    DEFAULT_SOURCE_SYSTEM,
    normalize_name,
)
from app.importers.review_historical_rows import (
    FOOD_CATEGORY_COLUMNS,
    calculate_business_signature,
    decimal_value,
    find_row_issues,
    is_blank,
)
from app.models.delivery import Delivery
from app.models.delivery_item import DeliveryItem
from app.models.food_category import FoodCategory
from app.models.import_batch import ImportBatch
from app.models.import_row import ImportRow
from app.models.recipient_alias import RecipientAlias

CATEGORY_NAMES = {
    "produce": "Produce",
    "packaged": "Packaged",
    "dairy": "Dairy",
    "meat": "Meat",
    "prepared_food": "Prepared Food",
    "water": "Water",
    "bread": "Bread",
    "other": "Other",
    "packaged_produce": "Packaged Produce",
}


def clean_optional(value: object) -> str | None:
    if is_blank(value):
        return None

    return str(value).strip()


def parse_delivery_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    try:
        return datetime.fromisoformat(text).date()
    except ValueError as error:
        raise ValueError(f"invalid delivery date: {value}") from error


def build_item_weights(
    raw_data: dict[str, object],
) -> dict[str, Decimal]:
    weights: dict[str, Decimal] = {}

    for column, category_code in FOOD_CATEGORY_COLUMNS.items():
        value = decimal_value(raw_data.get(column))

        if value is None:
            raise ValueError(f"food column {column} contains a nonnumeric value")

        if value < 0:
            raise ValueError(f"food column {column} contains a negative weight")

        if value > 0:
            weights[category_code] = value

    return weights


def additional_row_issues(
    raw_data: dict[str, object],
    alias: RecipientAlias | None,
) -> list[str]:
    issues: list[str] = []

    if not is_blank(raw_data.get("B")):
        try:
            parse_delivery_date(raw_data["B"])
        except ValueError:
            issues.append("delivery date is invalid")

    for column in FOOD_CATEGORY_COLUMNS:
        value = decimal_value(raw_data.get(column))

        if value is not None and value < 0:
            issues.append(f"food column {column} contains a negative weight")

    total_pounds = decimal_value(raw_data.get("P"))

    if total_pounds is not None and total_pounds < 0:
        issues.append("recorded total pounds is negative")

    if alias is None:
        issues.append("recipient alias not found")
    elif alias.decision == "exclude":
        issues.append("recipient alias is excluded")
    elif alias.recipient_site_id is None:
        issues.append("recipient alias has no canonical recipient")

    return issues


def synchronize_food_categories(
    db: Session,
) -> tuple[int, int]:
    existing = {category.code: category for category in db.scalars(select(FoodCategory)).all()}

    created = 0
    updated = 0

    for code, name in CATEGORY_NAMES.items():
        category = existing.get(code)

        if category is None:
            db.add(
                FoodCategory(
                    code=code,
                    name=name,
                    is_active=True,
                )
            )
            created += 1
            continue

        changed = False

        if category.name != name:
            category.name = name
            changed = True

        if not category.is_active:
            category.is_active = True
            changed = True

        if changed:
            updated += 1

    return created, updated


def promote_batch(
    db: Session,
    batch_id: uuid.UUID,
    source_system: str,
    commit: bool,
) -> dict[str, object]:
    batch = db.get(ImportBatch, batch_id)

    if batch is None:
        raise ValueError(f"batch not found: {batch_id}")

    rows = list(
        db.scalars(
            select(ImportRow).where(ImportRow.batch_id == batch_id).order_by(ImportRow.row_number)
        )
    )

    signature_counts = Counter(calculate_business_signature(row.raw_data) for row in rows)

    aliases = {
        alias.normalized_name: alias
        for alias in db.scalars(
            select(RecipientAlias).where(RecipientAlias.source_system == source_system)
        ).all()
    }

    existing_deliveries = list(
        db.scalars(select(Delivery).where(Delivery.source_system == source_system))
    )

    existing_by_import_row = {
        delivery.import_row_id: delivery
        for delivery in existing_deliveries
        if delivery.import_row_id is not None
    }
    existing_by_source_id = {
        delivery.source_record_id: delivery
        for delivery in existing_deliveries
        if delivery.source_record_id is not None
    }

    categories_created, categories_updated = synchronize_food_categories(db)

    db.flush()

    deliveries_created = 0
    delivery_items_created = 0
    already_imported = 0
    review_rows = 0
    rejected_rows = 0
    imported_pounds = Decimal("0")
    issue_counts: Counter[str] = Counter()
    pending_delivery_items: list[DeliveryItem] = []

    for row in rows:
        if row.status == "rejected":
            rejected_rows += 1
            continue

        source_record_id = row.source_record_id.strip() if row.source_record_id else None

        existing_delivery = existing_by_import_row.get(row.id)

        if existing_delivery is None and source_record_id is not None:
            existing_delivery = existing_by_source_id.get(source_record_id)

        if existing_delivery is not None:
            row.status = "imported"
            row.validation_issues = []
            already_imported += 1
            continue

        recipient_name = str(row.raw_data.get("C") or "").strip()
        alias = aliases.get(normalize_name(recipient_name))

        signature = calculate_business_signature(row.raw_data)
        issues = find_row_issues(
            raw_data=row.raw_data,
            existing_issues=validate_raw_row(row.raw_data),
            is_possible_duplicate=(signature_counts[signature] > 1),
        )
        issues.extend(
            additional_row_issues(
                row.raw_data,
                alias,
            )
        )
        issues = list(dict.fromkeys(issues))

        if issues:
            row.status = "needs_review"
            row.validation_issues = issues
            review_rows += 1
            issue_counts.update(issues)
            continue

        if alias is None or alias.recipient_site_id is None:
            raise RuntimeError(f"recipient resolution failed for row {row.row_number}")

        total_pounds = decimal_value(row.raw_data.get("P"))

        if total_pounds is None:
            raise RuntimeError(f"total parsing failed for row {row.row_number}")

        delivery_id = uuid.uuid4()

        delivery = Delivery(
            id=delivery_id,
            recipient_site_id=alias.recipient_site_id,
            import_row_id=row.id,
            source_system=source_system,
            source_record_id=source_record_id,
            delivery_date=parse_delivery_date(row.raw_data["B"]),
            source_recipient_name=recipient_name,
            recipient_location=clean_optional(row.raw_data.get("D")),
            driver_name=clean_optional(row.raw_data.get("E")),
            vehicle_name=clean_optional(row.raw_data.get("F")),
            total_pounds=total_pounds,
        )
        db.add(delivery)

        item_weights = build_item_weights(row.raw_data)

        for category_code, pounds in item_weights.items():
            pending_delivery_items.append(
                DeliveryItem(
                    id=uuid.uuid4(),
                    delivery_id=delivery_id,
                    food_category_code=category_code,
                    pounds=pounds,
                )
            )
            delivery_items_created += 1

        existing_by_import_row[row.id] = delivery

        if source_record_id is not None:
            existing_by_source_id[source_record_id] = delivery

        row.status = "imported"
        row.validation_issues = []
        deliveries_created += 1
        imported_pounds += total_pounds

    unresolved_rows = review_rows + rejected_rows
    batch.review_rows = unresolved_rows

    if unresolved_rows == 0:
        batch.status = "completed"
        batch.completed_at = datetime.now(UTC)
    else:
        batch.status = "staged"
        batch.completed_at = None

    # Insert delivery parent records before delivery item children.
    db.flush()

    db.add_all(pending_delivery_items)
    db.flush()

    summary: dict[str, object] = {
        "batch_id": str(batch_id),
        "total_staged_rows": len(rows),
        "deliveries_created": deliveries_created,
        "delivery_items_created": delivery_items_created,
        "already_imported": already_imported,
        "review_rows": review_rows,
        "rejected_rows": rejected_rows,
        "imported_total_pounds": str(imported_pounds),
        "food_categories_created": categories_created,
        "food_categories_updated": categories_updated,
        "issue_counts": dict(sorted(issue_counts.items())),
        "batch_status": batch.status,
        "committed": commit,
    }

    if commit:
        db.commit()
    else:
        db.rollback()

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote staged historical delivery rows.")
    parser.add_argument(
        "--batch-id",
        required=True,
        type=uuid.UUID,
    )
    parser.add_argument(
        "--source-system",
        default=DEFAULT_SOURCE_SYSTEM,
    )
    parser.add_argument(
        "--commit",
        action="store_true",
    )
    arguments = parser.parse_args()

    with SessionLocal() as db:
        try:
            summary = promote_batch(
                db=db,
                batch_id=arguments.batch_id,
                source_system=arguments.source_system,
                commit=arguments.commit,
            )
        except Exception:
            db.rollback()
            raise

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
