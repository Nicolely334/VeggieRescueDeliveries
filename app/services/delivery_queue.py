import uuid
from dataclasses import dataclass
from datetime import date, timedelta

TIE_WINDOW_DAYS = 3


@dataclass(frozen=True)
class QueueCandidate:
    recipient_site_id: uuid.UUID
    name: str
    priority: int
    last_delivery_date: date | None
    days_since_last_delivery: int | None
    is_overdue: bool
    deliveries_last_30_days: int
    pounds_last_30_days: float
    total_deliveries: int
    total_pounds: float
    reason: str


def rank_delivery_queue(
    candidates: list[QueueCandidate],
) -> list[QueueCandidate]:
    never_delivered = sorted(
        (candidate for candidate in candidates if candidate.last_delivery_date is None),
        key=lambda candidate: (
            candidate.priority,
            candidate.name.casefold(),
        ),
    )

    previously_delivered = sorted(
        (candidate for candidate in candidates if candidate.last_delivery_date is not None),
        key=lambda candidate: (
            candidate.last_delivery_date or date.max,
            candidate.name.casefold(),
        ),
    )

    ranked = list(never_delivered)
    index = 0

    while index < len(previously_delivered):
        anchor_date = previously_delivered[index].last_delivery_date
        assert anchor_date is not None

        cohort: list[QueueCandidate] = []

        while index < len(previously_delivered):
            candidate = previously_delivered[index]
            candidate_date = candidate.last_delivery_date
            assert candidate_date is not None

            if candidate_date > anchor_date + timedelta(days=TIE_WINDOW_DAYS):
                break

            cohort.append(candidate)
            index += 1

        cohort.sort(
            key=lambda candidate: (
                candidate.priority,
                candidate.last_delivery_date or date.max,
                candidate.name.casefold(),
            )
        )
        ranked.extend(cohort)

    return ranked
