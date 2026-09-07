import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.recipient_alias import RecipientAlias
from app.models.recipient_site import RecipientSite

DEFAULT_SOURCE_SYSTEM = "google_sheets_delivery_master"
VALID_DECISIONS = {"include", "merge", "exclude"}

REQUIRED_COLUMNS = (
    "source_name",
    "approved_decision",
    "approved_canonical_name",
    "approved_priority",
    "approved_is_fallback",
    "approved_is_active",
    "review_notes",
)


@dataclass(frozen=True)
class MappingRow:
    source_name: str
    normalized_name: str
    decision: str
    canonical_name: str | None
    priority: int | None
    is_fallback: bool | None
    is_active: bool | None
    notes: str | None


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.casefold()
    normalized = re.sub(r"[’‘`]", "'", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def get_cell(row: dict[str, str | None], column: str) -> str:
    return (row.get(column) or "").strip()


def parse_bool(value: str, column: str, line_number: int) -> bool:
    normalized = value.casefold()

    if normalized in {"true", "yes", "1"}:
        return True

    if normalized in {"false", "no", "0"}:
        return False

    raise ValueError(f"line {line_number}: {column} must be TRUE or FALSE")


def parse_priority(value: str, line_number: int) -> int:
    try:
        numeric_priority = float(value)
    except ValueError as error:
        raise ValueError(f"line {line_number}: approved_priority must be a number") from error

    if not numeric_priority.is_integer():
        raise ValueError(f"line {line_number}: approved_priority must be an integer")

    priority = int(numeric_priority)

    if priority not in range(1, 6):
        raise ValueError(f"line {line_number}: approved_priority must be from 1 to 5")

    return priority


def load_mapping_rows(file_path: Path) -> list[MappingRow]:
    with file_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as mapping_file:
        reader = csv.DictReader(mapping_file)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = set(REQUIRED_COLUMNS) - fieldnames

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"mapping is missing columns: {missing}")

        mapping_rows: list[MappingRow] = []
        seen_names: dict[str, int] = {}

        for line_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue

            source_name = get_cell(row, "source_name")
            decision = get_cell(row, "approved_decision").casefold()

            if not source_name:
                raise ValueError(f"line {line_number}: source_name is required")

            if decision not in VALID_DECISIONS:
                raise ValueError(f"line {line_number}: invalid approved_decision")

            normalized_name = normalize_name(source_name)

            if normalized_name in seen_names:
                earlier_line = seen_names[normalized_name]
                raise ValueError(
                    f"line {line_number}: duplicate source_name; first seen on line {earlier_line}"
                )

            seen_names[normalized_name] = line_number
            notes = get_cell(row, "review_notes") or None

            if decision == "exclude":
                mapping_rows.append(
                    MappingRow(
                        source_name=source_name,
                        normalized_name=normalized_name,
                        decision=decision,
                        canonical_name=None,
                        priority=None,
                        is_fallback=None,
                        is_active=None,
                        notes=notes,
                    )
                )
                continue

            canonical_name = get_cell(
                row,
                "approved_canonical_name",
            )

            if not canonical_name:
                raise ValueError(f"line {line_number}: approved_canonical_name is required")

            mapping_rows.append(
                MappingRow(
                    source_name=source_name,
                    normalized_name=normalized_name,
                    decision=decision,
                    canonical_name=canonical_name,
                    priority=parse_priority(
                        get_cell(row, "approved_priority"),
                        line_number,
                    ),
                    is_fallback=parse_bool(
                        get_cell(row, "approved_is_fallback"),
                        "approved_is_fallback",
                        line_number,
                    ),
                    is_active=parse_bool(
                        get_cell(row, "approved_is_active"),
                        "approved_is_active",
                        line_number,
                    ),
                    notes=notes,
                )
            )

    return mapping_rows


def collect_canonical_profiles(
    rows: list[MappingRow],
) -> dict[str, MappingRow]:
    profiles: dict[str, MappingRow] = {}

    for row in rows:
        if row.canonical_name is None:
            continue

        canonical_key = normalize_name(row.canonical_name)
        existing = profiles.get(canonical_key)

        if existing is None:
            profiles[canonical_key] = row
            continue

        existing_values = (
            existing.priority,
            existing.is_fallback,
            existing.is_active,
        )
        proposed_values = (
            row.priority,
            row.is_fallback,
            row.is_active,
        )

        if existing_values != proposed_values:
            raise ValueError(f"conflicting approvals for {row.canonical_name}")

    return profiles


def synchronize_mapping(
    db: Session,
    rows: list[MappingRow],
    source_system: str,
    commit: bool,
) -> dict[str, object]:
    profiles = collect_canonical_profiles(rows)

    sites_by_name: dict[str, RecipientSite] = {}

    for site in db.scalars(select(RecipientSite)).all():
        normalized_name = normalize_name(site.name)

        if normalized_name in sites_by_name:
            raise ValueError(f"duplicate canonical recipient site: {site.name}")

        sites_by_name[normalized_name] = site

    sites_created = 0
    sites_updated = 0

    for canonical_key, profile in profiles.items():
        assert profile.canonical_name is not None
        assert profile.priority is not None
        assert profile.is_fallback is not None
        assert profile.is_active is not None

        site = sites_by_name.get(canonical_key)

        if site is None:
            site = RecipientSite(
                name=profile.canonical_name,
                priority=profile.priority,
                is_fallback=profile.is_fallback,
                is_active=profile.is_active,
            )
            db.add(site)
            sites_by_name[canonical_key] = site
            sites_created += 1
            continue

        changes = {
            "name": profile.canonical_name,
            "priority": profile.priority,
            "is_fallback": profile.is_fallback,
            "is_active": profile.is_active,
        }
        changed = False

        for field_name, value in changes.items():
            if getattr(site, field_name) != value:
                setattr(site, field_name, value)
                changed = True

        if changed:
            sites_updated += 1

    db.flush()

    aliases_by_name = {
        alias.normalized_name: alias
        for alias in db.scalars(
            select(RecipientAlias).where(RecipientAlias.source_system == source_system)
        ).all()
    }

    aliases_created = 0
    aliases_updated = 0

    for row in rows:
        recipient_site_id = None

        if row.canonical_name is not None:
            canonical_key = normalize_name(row.canonical_name)
            recipient_site_id = sites_by_name[canonical_key].id

        alias = aliases_by_name.get(row.normalized_name)
        values = {
            "source_name": row.source_name,
            "decision": row.decision,
            "recipient_site_id": recipient_site_id,
            "notes": row.notes,
        }

        if alias is None:
            alias = RecipientAlias(
                source_system=source_system,
                normalized_name=row.normalized_name,
                **values,
            )
            db.add(alias)
            aliases_by_name[row.normalized_name] = alias
            aliases_created += 1
            continue

        changed = False

        for field_name, value in values.items():
            if getattr(alias, field_name) != value:
                setattr(alias, field_name, value)
                changed = True

        if changed:
            aliases_updated += 1

    db.flush()

    summary: dict[str, object] = {
        "total_mapping_rows": len(rows),
        "decision_counts": dict(sorted(Counter(row.decision for row in rows).items())),
        "canonical_sites": len(profiles),
        "recipient_sites_created": sites_created,
        "recipient_sites_updated": sites_updated,
        "aliases_created": aliases_created,
        "aliases_updated": aliases_updated,
        "committed": commit,
    }

    if commit:
        db.commit()
    else:
        db.rollback()

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
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

    rows = load_mapping_rows(arguments.file)

    with SessionLocal() as db:
        try:
            summary = synchronize_mapping(
                db,
                rows,
                arguments.source_system,
                arguments.commit,
            )
        except Exception:
            db.rollback()
            raise

    summary["file"] = str(arguments.file)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
