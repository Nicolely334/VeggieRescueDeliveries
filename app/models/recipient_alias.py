import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecipientAlias(Base):
    __tablename__ = "recipient_aliases"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('include', 'merge', 'exclude')",
            name="valid_decision",
        ),
        UniqueConstraint(
            "source_system",
            "normalized_name",
            name="source_name_per_system",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    normalized_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    recipient_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipient_sites.id"),
        nullable=True,
        index=True,
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
