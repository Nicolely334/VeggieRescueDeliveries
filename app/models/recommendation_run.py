import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"
    __table_args__ = (
        CheckConstraint(
            "tie_window_days >= 0",
            name="nonnegative_tie_window_days",
        ),
        CheckConstraint(
            "offered_total_pounds > 0",
            name="positive_offered_total_pounds",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    donation_offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donation_offers.id"),
        nullable=False,
        index=True,
    )
    as_of_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1",
        server_default="v1",
    )
    tie_window_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    offered_total_pounds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    offered_items_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
