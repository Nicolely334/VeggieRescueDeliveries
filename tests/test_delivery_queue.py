import uuid
from datetime import date

from app.services.delivery_queue import (
    QueueCandidate,
    rank_delivery_queue,
)


def candidate(
    name: str,
    priority: int,
    last_delivery_date: date | None,
) -> QueueCandidate:
    return QueueCandidate(
        recipient_site_id=uuid.uuid4(),
        name=name,
        priority=priority,
        last_delivery_date=last_delivery_date,
        days_since_last_delivery=None,
        is_overdue=True,
        deliveries_last_30_days=0,
        pounds_last_30_days=0,
        total_deliveries=0,
        total_pounds=0,
        reason="Test",
    )


def test_never_delivered_recipient_is_first() -> None:
    ranked = rank_delivery_queue(
        [
            candidate(
                "Previously Served",
                1,
                date(2026, 1, 1),
            ),
            candidate("Never Served", 3, None),
        ]
    )

    assert ranked[0].name == "Never Served"


def test_priority_breaks_three_day_tie() -> None:
    ranked = rank_delivery_queue(
        [
            candidate(
                "Older Low Priority",
                4,
                date(2026, 1, 1),
            ),
            candidate(
                "Newer High Priority",
                1,
                date(2026, 1, 3),
            ),
        ]
    )

    assert ranked[0].name == "Newer High Priority"


def test_oldest_date_wins_outside_tie_window() -> None:
    ranked = rank_delivery_queue(
        [
            candidate(
                "Older Low Priority",
                5,
                date(2026, 1, 1),
            ),
            candidate(
                "Newer High Priority",
                1,
                date(2026, 1, 5),
            ),
        ]
    )

    assert ranked[0].name == "Older Low Priority"
