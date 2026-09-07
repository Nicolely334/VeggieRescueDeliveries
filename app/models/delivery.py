import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "total_pounds >= 0",
            name="nonnegative_total_pounds",
        ),
        UniqueConstraint(
            "source_system",
            "source_record_id",
            name="source_record",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recipient_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipient_sites.id"),
        nullable=False,
        index=True,
    )
    import_row_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_rows.id"),
        nullable=True,
        unique=True,
    )
    source_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    source_record_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    delivery_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    source_recipient_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
    recipient_location: Mapped[str | None] = mapped_column(
        String(300),
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
    total_pounds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
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
