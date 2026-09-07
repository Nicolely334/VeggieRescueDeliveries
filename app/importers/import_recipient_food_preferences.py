import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.importers.import_recipient_mapping import (
    normalize_name,
)
from app.models.food_category import FoodCategory
from app.models.recipient_food_preference import (
    RecipientFoodPreference,
)
from app.models.recipient_site import RecipientSite

VALID_DECISIONS = {
    "include",
    "merge",
    "exclude",
}

REQUIRED_COLUMNS = (
    "source_name",
    "accepted_food",
    "approved_decision",
    "approved_canonical_name",
)


@dataclass(frozen=True)
class PreferenceMappingRow:
    source_name: str
    canonical_name: str
    accepted_food: str


def clean_food_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.casefold(),
    ).strip()


def category_codes_for_food(
    accepted_food: str,
    all_category_codes: set[str],
) -> set[str]:
    normalized = clean_food_text(accepted_food)

    if not normalized:
        return set()

    if normalized.startswith("anything"):
        return set(all_category_codes)

    category_codes: set[str] = set()

    if any(
        keyword in normalized
        for keyword in (
            "produce",
            "fruit",
            "veggie",
            "vegetable",
        )
    ):
        category_codes.add("produce")

    if "bread" in normalized:
        category_codes.add("bread")

    if "prepared food" in normalized:
        category_codes.add("prepared_food")

    return category_codes


def load_preference_rows(
    file_path: Path,
) -> list[PreferenceMappingRow]:
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

        rows: list[PreferenceMappingRow] = []

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            if not any((value or "").strip() for value in row.values()):
                continue

            source_name = (row.get("source_name") or "").strip()
            decision = (row.get("approved_decision") or "").strip().casefold()

            if not source_name:
                raise ValueError(f"line {line_number}: source_name is required")

            if decision not in VALID_DECISIONS:
                raise ValueError(f"line {line_number}: invalid approved_decision")

            if decision == "exclude":
                continue

            canonical_name = (row.get("approved_canonical_name") or "").strip()

            if not canonical_name:
                raise ValueError(f"line {line_number}: approved_canonical_name is required")

            accepted_food = (row.get("accepted_food") or "").strip()

            rows.append(
                PreferenceMappingRow(
                    source_name=source_name,
                    canonical_name=canonical_name,
                    accepted_food=accepted_food,
                )
            )

    return rows


def build_import_note(
    source_values: set[str],
) -> str:
    ordered_values = sorted(
        source_values,
        key=str.casefold,
    )

    return "Imported from approved recipient mapping: " + "; ".join(ordered_values)


def synchronize_food_preferences(
    db: Session,
    rows: list[PreferenceMappingRow],
    commit: bool,
) -> dict[str, object]:
    active_category_codes = set(
        db.scalars(select(FoodCategory.code).where(FoodCategory.is_active.is_(True))).all()
    )

    if not active_category_codes:
        raise ValueError("no active food categories were found")

    profile_names: dict[str, str] = {}
    category_codes_by_profile: dict[
        str,
        set[str],
    ] = defaultdict(set)
    category_sources: dict[
        str,
        dict[str, set[str]],
    ] = defaultdict(lambda: defaultdict(set))
    unresolved_values: Counter[str] = Counter()

    for row in rows:
        profile_key = normalize_name(row.canonical_name)
        profile_names[profile_key] = row.canonical_name

        category_codes = category_codes_for_food(
            accepted_food=row.accepted_food,
            all_category_codes=(active_category_codes),
        )

        if row.accepted_food and not category_codes:
            unresolved_values[row.accepted_food] += 1

        for category_code in category_codes:
            category_codes_by_profile[profile_key].add(category_code)
            category_sources[profile_key][category_code].add(row.accepted_food)

    planned_codes = {
        category_code
        for category_codes in category_codes_by_profile.values()
        for category_code in category_codes
    }
    unavailable_codes = sorted(planned_codes - active_category_codes)

    if unavailable_codes:
        raise ValueError(
            "required food categories are unavailable: " + ", ".join(unavailable_codes)
        )

    sites_by_name = {
        normalize_name(site.name): site for site in db.scalars(select(RecipientSite)).all()
    }

    missing_sites = sorted(
        profile_names[profile_key]
        for profile_key in category_codes_by_profile
        if profile_key not in sites_by_name
    )

    if missing_sites:
        raise ValueError("recipient sites were not found: " + ", ".join(missing_sites))

    existing_preferences = db.scalars(select(RecipientFoodPreference)).all()

    existing_keys = {
        (
            preference.recipient_site_id,
            preference.food_category_code,
        )
        for preference in existing_preferences
    }

    preferences_created = 0
    preferences_existing = 0

    for (
        profile_key,
        category_codes,
    ) in category_codes_by_profile.items():
        site = sites_by_name[profile_key]

        for category_code in sorted(category_codes):
            preference_key = (
                site.id,
                category_code,
            )

            if preference_key in existing_keys:
                preferences_existing += 1
                continue

            source_values = category_sources[profile_key][category_code]

            db.add(
                RecipientFoodPreference(
                    recipient_site_id=site.id,
                    food_category_code=(category_code),
                    maximum_pounds=None,
                    notes=build_import_note(source_values),
                )
            )

            existing_keys.add(preference_key)
            preferences_created += 1

    db.flush()

    profiles_with_preferences = set(category_codes_by_profile)
    profiles_without_preferences = set(profile_names) - profiles_with_preferences

    summary: dict[str, object] = {
        "active_food_categories": len(active_category_codes),
        "canonical_profiles": len(profile_names),
        "profiles_with_preferences": len(profiles_with_preferences),
        "profiles_without_usable_preferences": (len(profiles_without_preferences)),
        "preference_links_planned": sum(
            len(category_codes) for category_codes in category_codes_by_profile.values()
        ),
        "preference_links_created": (preferences_created),
        "preference_links_existing": (preferences_existing),
        "unresolved_accepted_food_values": dict(sorted(unresolved_values.items())),
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
        "--commit",
        action="store_true",
    )
    arguments = parser.parse_args()

    rows = load_preference_rows(arguments.file)

    with SessionLocal() as db:
        try:
            summary = synchronize_food_preferences(
                db=db,
                rows=rows,
                commit=arguments.commit,
            )
        except Exception:
            db.rollback()
            raise

    summary["file"] = str(arguments.file)

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
