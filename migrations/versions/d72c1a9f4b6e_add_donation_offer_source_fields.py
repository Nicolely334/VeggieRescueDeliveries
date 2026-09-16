"""add donation offer source fields

Revision ID: d72c1a9f4b6e
Revises: a600f02c78d2
Create Date: 2026-09-15 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d72c1a9f4b6e"
down_revision: str | Sequence[str] | None = "a600f02c78d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "donation_offers",
        sa.Column(
            "source_system",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "donation_offers",
        sa.Column(
            "source_record_id",
            sa.String(length=200),
            nullable=True,
        ),
    )
    op.add_column(
        "donation_offers",
        sa.Column(
            "source_submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "donation_offers",
        sa.Column(
            "source_row_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_donation_offers_complete_source_identity"),
        "donation_offers",
        "(source_system IS NULL) = (source_record_id IS NULL)",
    )
    op.create_unique_constraint(
        "donation_offer_source_record",
        "donation_offers",
        [
            "source_system",
            "source_record_id",
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "donation_offer_source_record",
        "donation_offers",
        type_="unique",
    )
    op.drop_constraint(
        op.f("ck_donation_offers_complete_source_identity"),
        "donation_offers",
        type_="check",
    )
    op.drop_column(
        "donation_offers",
        "source_row_fingerprint",
    )
    op.drop_column(
        "donation_offers",
        "source_submitted_at",
    )
    op.drop_column(
        "donation_offers",
        "source_record_id",
    )
    op.drop_column(
        "donation_offers",
        "source_system",
    )