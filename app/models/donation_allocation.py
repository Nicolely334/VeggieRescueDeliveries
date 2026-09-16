import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DonationAllocation(Base):
    __tablename__ = "donation_allocations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'assigned', 'completed', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint(
            (
                "NOT is_override OR "
                "(override_reason IS NOT NULL "
                "AND char_length(btrim(override_reason)) > 0)"
            ),
            name="override_reason_required",
        ),
        Index(
            "uq_donation_allocations_active_offer_recipient",
            "donation_offer_id",
            "recipient_site_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
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
    recommendation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_runs.id"),
        nullable=False,
        index=True,
    )
    recipient_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipient_sites.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planned",
        server_default="planned",
        index=True,
    )
    is_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    override_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    driver_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    vehicle_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
