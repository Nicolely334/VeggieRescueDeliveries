import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecipientFoodPreference(Base):
    __tablename__ = "recipient_food_preferences"
    __table_args__ = (
        CheckConstraint(
            "maximum_pounds IS NULL OR maximum_pounds > 0",
            name="positive_maximum_pounds",
        ),
        UniqueConstraint(
            "recipient_site_id",
            "food_category_code",
            name="recipient_food_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recipient_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "recipient_sites.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    food_category_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("food_categories.code"),
        nullable=False,
        index=True,
    )
    maximum_pounds: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
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
