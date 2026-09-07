from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

from openpyxl import load_workbook

MISSING_RECIPIENT = "(missing recipient)"

VEHICLE_LABELS = {
    "14 foot truck",
    "14 ft truck",
    "18 foot truck",
    "ford van",
    "new van",
    "van",
}

# These are spelling/renaming corrections supported by the directory workbook.
# They are safe to apply automatically because each target identifies one site.
KNOWN_ALIASES = {
    "collectivo mariposa": "Colectivo Mariposa",
    "food bank sbc south county sharehouse": "Food Bank SBC-South County Sharehose",
    "lompoc teen center": "Lomoc Teen Center",
    "marthas farm sanctuary": "Martha's Farm Animal Sanctuary",
    "oxnard salvation army": "Salvation Army - Oxnard",
    "santa maria parks and recreation": "Santa Maria Recreation and Parks Department",
    "ucsb associated students food bank": "UCSB Associated Students Food Bank",
    "vista school district gaviota": "Vista del Mar Union School District",
}

# Correct obvious spelling errors before writing a canonical database name.
CANONICAL_NAME_OVERRIDES = {
    "food bank sbc south county sharehose": "Food Bank SBC-South County Sharehouse",
    "lomoc teen center": "Lompoc Teen Center",
    "micah mission": "Micah Mission",
}

OUTPUT_COLUMNS = [
    "source_name",
    "delivery_count",
    "first_delivery_date",
    "last_delivery_date",
    "observed_locations",
    "recorded_total_pounds",
    "directory_match_status",
    "match_confidence",
    "suggested_decision",
    "suggested_canonical_name",
    "suggested_priority",
    "suggested_region",
    "suggested_is_fallback",
    "suggested_is_active",
    "accepted_food",
    "organization_type",
    "demographic_served",
    "available_delivery_days",
    "review_reason",
    "approved_decision",
    "approved_canonical_name",
    "approved_priority",
    "approved_is_fallback",
    "approved_is_active",
    "review_notes",
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value).lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ").replace("foodbank", "food bank")
    text = text.replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def normalize_header(value: object) -> str:
    return normalize_name(value).replace(" ", "_")


def normalize_region(value: object) -> str:
    normalized = normalize_name(value)
    aliases = {
        "santa barbara goleta": "SB/Goleta",
        "sb goleta": "SB/Goleta",
        "santa maria orcutt": "SM/Orcutt",
        "sm orcutt": "SM/Orcutt",
        "santa ynez valley": "SYV",
        "syv": "SYV",
        "lompoc": "Lompoc",
        "guadalupe": "Guadalupe",
        "gaviota": "Gaviota",
        "ventura": "Ventura",
        "slo county": "SLO County",
        "los angeles": "Los Angeles",
        "los angelos": "Los Angeles",
    }
    return aliases.get(normalized, clean_text(value))


def as_number(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(clean_text(value))
    except ValueError:
        return 0.0


def as_priority(value: object) -> int | None:
    if value is None or clean_text(value) == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def as_iso_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def canonical_name(name: str) -> str:
    return CANONICAL_NAME_OVERRIDES.get(normalize_name(name), clean_text(name))


def find_column(headers: list[object], names: list[str], fallback: int | None = None) -> int:
    normalized = {normalize_header(header): index for index, header in enumerate(headers)}
    for name in names:
        index = normalized.get(normalize_header(name))
        if index is not None:
            return index
    if fallback is not None:
        return fallback
    raise ValueError(f"could not find any of these columns: {', '.join(names)}")


def row_value(row: tuple[object, ...], index: int) -> object:
    return row[index] if index < len(row) else None


@dataclass
class DeliveryStats:
    source_name: str
    delivery_count: int = 0
    dates: list[str] = field(default_factory=list)
    locations: Counter[str] = field(default_factory=Counter)
    recorded_total_pounds: float = 0.0


@dataclass
class RecipientProfile:
    name: str
    region: str = ""
    priority: int | None = None
    accepts: str = ""
    organization_type: str = ""
    demographic_served: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    available_delivery_days: str = ""
    notes: str = ""
    source_sheets: set[str] = field(default_factory=set)


def read_delivery_stats(master_file: Path) -> dict[str, DeliveryStats]:
    workbook = load_workbook(master_file, read_only=True, data_only=True)
    worksheet = workbook["Form responses"]
    rows = worksheet.iter_rows(values_only=True)
    headers = list(next(rows))

    date_index = find_column(headers, ["Delivery Date", "Delivery_Date"], fallback=1)
    recipient_index = find_column(
        headers,
        ["Food Recipient", "Food_Recipient"],
        fallback=2,
    )
    location_index = find_column(
        headers,
        ["Food Recipient Location", "Food_Recipient_Location"],
        fallback=3,
    )
    total_index = find_column(headers, ["Total Pounds", "Total_Pounds"], fallback=15)

    stats: dict[str, DeliveryStats] = {}
    for row in rows:
        source_name = clean_text(row_value(row, recipient_index)) or MISSING_RECIPIENT
        current = stats.setdefault(source_name, DeliveryStats(source_name=source_name))
        current.delivery_count += 1

        delivery_date = as_iso_date(row_value(row, date_index))
        if delivery_date:
            current.dates.append(delivery_date)

        region = normalize_region(row_value(row, location_index))
        if region:
            current.locations[region] += 1

        current.recorded_total_pounds += as_number(row_value(row, total_index))

    workbook.close()
    return stats


def worksheet_records(worksheet) -> list[dict[str, object]]:
    rows = worksheet.iter_rows(values_only=True)
    headers = [normalize_header(value) for value in next(rows)]
    return [
        {header: value for header, value in zip(headers, row, strict=False) if header}
        for row in rows
    ]


def first(record: dict[str, object], *names: str) -> object:
    for name in names:
        value = record.get(normalize_header(name))
        if clean_text(value):
            return value
    return None


def add_profile(
    profiles: dict[tuple[str, str], RecipientProfile],
    record: dict[str, object],
    source_sheet: str,
) -> None:
    name = clean_text(first(record, "Name", "Recipient Name"))
    if not name:
        return

    region = normalize_region(first(record, "location", "Location"))
    key = (normalize_name(name), normalize_name(region))
    profile = profiles.setdefault(key, RecipientProfile(name=name, region=region))
    profile.source_sheets.add(source_sheet)

    # Food_Recipients is preferred for descriptive fields. Mapping is preferred
    # for geographic and current delivery-instruction fields.
    values = {
        "priority": as_priority(first(record, "priority", "Priority")),
        "accepts": clean_text(first(record, "Accepts", "Food they will accept")),
        "organization_type": clean_text(first(record, "Org Type")),
        "demographic_served": clean_text(first(record, "Demographic Served")),
        "address": clean_text(first(record, "Address", "Mailing Address")),
        "available_delivery_days": clean_text(first(record, "available delivery days")),
        "notes": clean_text(first(record, "Notes")),
    }

    for attribute, value in values.items():
        if value not in (None, ""):
            if source_sheet == "Mapping" or getattr(profile, attribute) in (None, ""):
                setattr(profile, attribute, value)

    latitude = first(record, "latitude")
    longitude = first(record, "longitude")
    if isinstance(latitude, int | float):
        profile.latitude = float(latitude)
    if isinstance(longitude, int | float):
        profile.longitude = float(longitude)


def read_recipient_profiles(directory_file: Path) -> list[RecipientProfile]:
    workbook = load_workbook(directory_file, read_only=True, data_only=True)
    profiles: dict[tuple[str, str], RecipientProfile] = {}

    for sheet_name in ["Food_Recipients", "Mapping", "Recipient Details"]:
        worksheet = workbook[sheet_name]
        for record in worksheet_records(worksheet):
            add_profile(profiles, record, sheet_name)

    workbook.close()
    return list(profiles.values())


def choose_by_region(
    candidates: list[RecipientProfile],
    observed_locations: Counter[str],
) -> RecipientProfile | None:
    observed = {normalize_name(location) for location in observed_locations}
    matches = [
        candidate
        for candidate in candidates
        if normalize_name(candidate.region) in observed and normalize_name(candidate.region)
    ]
    return matches[0] if len(matches) == 1 else None


def choose_profile(
    candidates: list[RecipientProfile],
    observed_locations: Counter[str],
) -> RecipientProfile | None:
    if len(candidates) == 1:
        return candidates[0]

    region_match = choose_by_region(candidates, observed_locations)
    if region_match is not None:
        return region_match

    # Recipient Details contains older partial copies. Prefer the single current
    # profile carrying an operational priority when that resolves the duplicate.
    prioritized = [candidate for candidate in candidates if candidate.priority is not None]
    return prioritized[0] if len(prioritized) == 1 else None


def best_fuzzy_match(
    source_name: str,
    profiles: list[RecipientProfile],
) -> tuple[RecipientProfile | None, float]:
    source = normalize_name(source_name)
    scored = [
        (SequenceMatcher(None, source, normalize_name(profile.name)).ratio(), profile)
        for profile in profiles
    ]
    if not scored:
        return None, 0.0
    confidence, profile = max(scored, key=lambda item: item[0])
    return profile, confidence


def fallback_suggestion(profile: RecipientProfile) -> tuple[bool, bool]:
    searchable = normalize_name(
        " ".join([profile.name, profile.accepts, profile.organization_type, profile.notes])
    )
    fallback = (
        (profile.priority is not None and profile.priority > 5)
        or "only when we have extra" in searchable
        or profile.organization_type.lower() in {"animals", "compost"}
    )
    policy_review = fallback or (profile.priority is not None and profile.priority > 5)
    return fallback, policy_review


def active_suggestion(profile: RecipientProfile) -> tuple[bool, bool]:
    inactive = "not active" in normalize_name(profile.notes)
    return not inactive, inactive


def load_previous_approvals(output_file: Path) -> dict[str, dict[str, str]]:
    if not output_file.exists():
        return {}

    with output_file.open(newline="", encoding="utf-8-sig") as handle:
        return {
            clean_text(row.get("source_name")): row
            for row in csv.DictReader(handle)
            if clean_text(row.get("source_name"))
        }


def build_mapping_rows(
    delivery_stats: dict[str, DeliveryStats],
    profiles: list[RecipientProfile],
    previous: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    profiles_by_name: dict[str, list[RecipientProfile]] = defaultdict(list)
    for profile in profiles:
        profiles_by_name[normalize_name(profile.name)].append(profile)

    result: list[dict[str, object]] = []
    for stats in delivery_stats.values():
        source_normalized = normalize_name(stats.source_name)
        match_status = "no_match"
        confidence = 0.0
        suggested_decision = ""
        review_reason = ""
        candidate: RecipientProfile | None = None
        safe_to_approve = False

        if stats.source_name == MISSING_RECIPIENT:
            match_status = "missing_recipient"
            review_reason = "source row has no recipient"
        elif source_normalized in VEHICLE_LABELS:
            match_status = "invalid_vehicle_label"
            review_reason = "vehicle name was entered in the recipient field"
        else:
            exact_candidates = profiles_by_name.get(source_normalized, [])
            if (
                exact_candidates
                and (candidate := choose_profile(exact_candidates, stats.locations)) is not None
            ):
                match_status = "exact"
                confidence = 1.0
                suggested_decision = "include"
                safe_to_approve = True
            elif exact_candidates:
                match_status = "ambiguous_directory_match"
                confidence = 1.0
                review_reason = "multiple directory sites use this name"
            elif alias_target := KNOWN_ALIASES.get(source_normalized):
                alias_candidates = profiles_by_name.get(normalize_name(alias_target), [])
                candidate = choose_profile(alias_candidates, stats.locations)
                if candidate is not None:
                    match_status = "known_alias"
                    confidence = 1.0
                    suggested_decision = "merge"
                    safe_to_approve = True
                else:
                    review_reason = f"known alias target was not unique: {alias_target}"
            else:
                fuzzy_candidate, fuzzy_confidence = best_fuzzy_match(stats.source_name, profiles)
                if fuzzy_candidate is not None and fuzzy_confidence >= 0.72:
                    candidate = fuzzy_candidate
                    confidence = fuzzy_confidence
                    match_status = "fuzzy_suggestion"
                    suggested_decision = "merge"
                    review_reason = "fuzzy matches are suggestions and require approval"
                else:
                    review_reason = "no directory match found"

        suggested_priority: int | str = ""
        suggested_fallback: bool | str = ""
        suggested_active: bool | str = ""
        policy_review = False

        if candidate is not None:
            suggested_priority = candidate.priority or ""
            if candidate.priority is not None and candidate.priority > 5:
                suggested_priority = 5
                review_reason = "directory priority 6 requires approval as priority 5 fallback"

            suggested_fallback, fallback_review = fallback_suggestion(candidate)
            suggested_active, active_review = active_suggestion(candidate)
            policy_review = fallback_review or active_review
            if policy_review:
                safe_to_approve = False
                if not review_reason:
                    review_reason = "fallback or inactive status requires policy approval"

            if candidate.priority is None:
                safe_to_approve = False
                review_reason = review_reason or "directory profile has no priority"

        previous_row = previous.get(stats.source_name, {})
        approved = {
            column: clean_text(previous_row.get(column))
            for column in [
                "approved_decision",
                "approved_canonical_name",
                "approved_priority",
                "approved_is_fallback",
                "approved_is_active",
                "review_notes",
            ]
        }

        if safe_to_approve and not approved["approved_decision"] and candidate is not None:
            approved.update(
                {
                    "approved_decision": suggested_decision,
                    "approved_canonical_name": canonical_name(candidate.name),
                    "approved_priority": str(suggested_priority),
                    "approved_is_fallback": str(suggested_fallback).lower(),
                    "approved_is_active": str(suggested_active).lower(),
                }
            )

        row = {
            "source_name": stats.source_name,
            "delivery_count": stats.delivery_count,
            "first_delivery_date": min(stats.dates) if stats.dates else "",
            "last_delivery_date": max(stats.dates) if stats.dates else "",
            "observed_locations": " | ".join(stats.locations),
            "recorded_total_pounds": round(stats.recorded_total_pounds, 2),
            "directory_match_status": match_status,
            "match_confidence": round(confidence, 3) if confidence else "",
            "suggested_decision": suggested_decision,
            "suggested_canonical_name": canonical_name(candidate.name) if candidate else "",
            "suggested_priority": suggested_priority,
            "suggested_region": candidate.region if candidate else "",
            "suggested_is_fallback": (
                str(suggested_fallback).lower() if suggested_fallback != "" else ""
            ),
            "suggested_is_active": (
                str(suggested_active).lower() if suggested_active != "" else ""
            ),
            "accepted_food": candidate.accepts if candidate else "",
            "organization_type": candidate.organization_type if candidate else "",
            "demographic_served": candidate.demographic_served if candidate else "",
            "available_delivery_days": candidate.available_delivery_days if candidate else "",
            "review_reason": review_reason,
            **approved,
        }
        result.append(row)

    return sorted(
        result,
        key=lambda row: (
            bool(row["approved_decision"]),
            -int(row["delivery_count"]),
            str(row["source_name"]).lower(),
        ),
    )


def write_mapping(output_file: Path, rows: list[dict[str, object]]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_suffix(f"{output_file.suffix}.tmp")

    with temporary_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    temporary_file.replace(output_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an approval-ready recipient mapping from both source workbooks."
    )
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--directory-file", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/recipient_mapping.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    previous = load_previous_approvals(args.output)
    delivery_stats = read_delivery_stats(args.master_file)
    profiles = read_recipient_profiles(args.directory_file)
    rows = build_mapping_rows(delivery_stats, profiles, previous)
    write_mapping(args.output, rows)

    auto_approved = sum(bool(row["approved_decision"]) for row in rows)
    summary = {
        "auto_approved_labels": auto_approved,
        "labels_needing_review": len(rows) - auto_approved,
        "output": str(args.output.resolve()),
        "recipient_profiles": len(profiles),
        "source_labels": len(rows),
        "source_rows": sum(int(row["delivery_count"]) for row in rows),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
