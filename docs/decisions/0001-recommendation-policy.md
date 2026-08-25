# ADR 0001: Equitable recommendation policy

## Status

Accepted

## Context

Veggie Rescue needs to distribute donated food equitably among eligible
recipient sites. The application is used by David. Recipients and drivers
do not have application accounts.

## Decision

The recommendation engine will use deterministic, explainable rules rather
than machine learning.

1. Filter out inactive or ineligible recipients.
2. Recipients with no completed delivery history come first.
3. Otherwise, the recipient with the oldest completed delivery comes first.
4. Delivery dates within three days are treated as a close tie.
5. Close ties are resolved using:
   1. Higher priority, where 1 is highest and 5 is lowest.
   2. Better food and quantity fit.
   3. Shorter distance from the farm.
6. Thirty days without a delivery means overdue, but does not cap recency.
7. David must provide a reason when rejecting a recommendation.
8. A rejected recipient is excluded from that donation only.
9. Donations may be divided among multiple recipients.
10. Only completed deliveries using actual delivered quantities affect recency.
11. Compost and other fallback destinations are excluded from the normal queue.
12. Every recommendation and decision must be retained for auditing.

## Consequences

The recommendation process will be transparent and testable. Historical
delivery selections will not be treated as machine-learning labels.