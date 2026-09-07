from app.importers.create_recipient_mapping import (
    build_recipient_summaries,
    suggest_mapping,
)


def test_recipient_deliveries_are_summarized() -> None:
    raw_rows = [
        {
            "B": "2025-01-02",
            "C": "Community Pantry",
            "D": "Lompoc",
            "P": 100,
        },
        {
            "B": "2025-02-03",
            "C": "Community Pantry",
            "D": "Santa Barbara/Goleta",
            "P": 75,
        },
    ]

    summaries, missing_rows = build_recipient_summaries(raw_rows)

    assert missing_rows == 0
    assert len(summaries) == 1

    summary = summaries[0]

    assert summary["source_name"] == "Community Pantry"
    assert summary["delivery_count"] == 2
    assert summary["first_delivery_date"] == "2025-01-02"
    assert summary["last_delivery_date"] == "2025-02-03"
    assert summary["recorded_total_pounds"] == "175"


def test_missing_recipient_is_counted() -> None:
    summaries, missing_rows = build_recipient_summaries([{"B": "2025-01-02", "C": None, "P": 20}])

    assert summaries == []
    assert missing_rows == 1


def test_vehicle_recipient_is_suggested_for_exclusion() -> None:
    decision, canonical_name, reason = suggest_mapping("Ford Van")

    assert decision == "exclude"
    assert canonical_name == ""
    assert "vehicle" in reason


def test_possible_fallback_requires_review() -> None:
    decision, canonical_name, reason = suggest_mapping("Violet Sage Walker Goats")

    assert decision == "review"
    assert canonical_name == "Violet Sage Walker Goats"
    assert "fallback" in reason
