import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'pending',
                'needs_review',
                'approved',
                'rejected',
                'imported'
            )
            """,
            name="valid_status",
        ),
        UniqueConstraint(
            "batch_id",
            "sheet_name",
            "row_number",
            name="batch_sheet_row",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "import_batches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    sheet_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source_record_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    row_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    raw_data: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    validation_issues: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
