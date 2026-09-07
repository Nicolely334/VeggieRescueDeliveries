import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecommendationCandidate(Base):
    __tablename__ = "recommendation_candidates"
    __table_args__ = (
        CheckConstraint(
            "rank > 0",
            name="positive_rank",
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="priority_range",
        ),
        CheckConstraint(
            ("days_since_last_delivery IS NULL OR days_since_last_delivery >= 0"),
            name="nonnegative_days_since_last_delivery",
        ),
        CheckConstraint(
            "deliveries_last_30_days >= 0",
            name="nonnegative_recent_deliveries",
        ),
        CheckConstraint(
            "pounds_last_30_days >= 0",
            name="nonnegative_recent_pounds",
        ),
        CheckConstraint(
            "total_deliveries >= 0",
            name="nonnegative_total_deliveries",
        ),
        CheckConstraint(
            "total_pounds >= 0",
            name="nonnegative_total_pounds",
        ),
        CheckConstraint(
            "matched_category_count > 0",
            name="positive_matched_category_count",
        ),
        CheckConstraint(
            "known_potential_pounds >= 0",
            name="nonnegative_known_potential_pounds",
        ),
        UniqueConstraint(
            "recommendation_run_id",
            "recipient_site_id",
            name="recommendation_run_recipient",
        ),
        UniqueConstraint(
            "recommendation_run_id",
            "rank",
            name="recommendation_run_rank",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recommendation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "recommendation_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    recipient_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipient_sites.id"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    recipient_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    last_delivery_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    days_since_last_delivery: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    is_overdue: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    deliveries_last_30_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    pounds_last_30_days: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    total_deliveries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_pounds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    matched_category_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    known_potential_pounds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    has_unknown_capacity: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    food_matches_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
