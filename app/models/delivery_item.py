import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
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


class DeliveryItem(Base):
    __tablename__ = "delivery_items"
    __table_args__ = (
        CheckConstraint(
            "pounds > 0",
            name="positive_pounds",
        ),
        UniqueConstraint(
            "delivery_id",
            "food_category_code",
            name="delivery_food_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "deliveries.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    food_category_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("food_categories.code"),
        nullable=False,
    )
    pounds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
