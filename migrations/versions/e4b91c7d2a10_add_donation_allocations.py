"""add donation allocations

Revision ID: e4b91c7d2a10
Revises: d72c1a9f4b6e
Create Date: 2026-09-15 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b91c7d2a10"
down_revision: str | Sequence[str] | None = "d72c1a9f4b6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "donation_allocations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_offer_id", sa.UUID(), nullable=False),
        sa.Column("recommendation_run_id", sa.UUID(), nullable=False),
        sa.Column("recipient_site_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="planned",
            nullable=False,
        ),
        sa.Column(
            "is_override",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("driver_name", sa.String(length=200), nullable=True),
        sa.Column("vehicle_name", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "NOT is_override OR "
                "(override_reason IS NOT NULL "
                "AND char_length(btrim(override_reason)) > 0)"
            ),
            name=op.f("ck_donation_allocations_override_reason_required"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'assigned', 'completed', 'cancelled')",
            name=op.f("ck_donation_allocations_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["donation_offer_id"],
            ["donation_offers.id"],
            name=op.f(
                "fk_donation_allocations_donation_offer_id_donation_offers"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["recipient_site_id"],
            ["recipient_sites.id"],
            name=op.f(
                "fk_donation_allocations_recipient_site_id_recipient_sites"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_run_id"],
            ["recommendation_runs.id"],
            name=op.f(
                "fk_donation_allocations_recommendation_run_id_recommendation_runs"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_donation_allocations"),
        ),
    )
    op.create_index(
        op.f("ix_donation_allocations_donation_offer_id"),
        "donation_allocations",
        ["donation_offer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_donation_allocations_recipient_site_id"),
        "donation_allocations",
        ["recipient_site_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_donation_allocations_recommendation_run_id"),
        "donation_allocations",
        ["recommendation_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_donation_allocations_status"),
        "donation_allocations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_donation_allocations_active_offer_recipient",
        "donation_allocations",
        ["donation_offer_id", "recipient_site_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    op.create_table(
        "donation_allocation_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_allocation_id", sa.UUID(), nullable=False),
        sa.Column("food_category_code", sa.String(length=50), nullable=False),
        sa.Column(
            "pounds",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "pounds > 0",
            name=op.f("ck_donation_allocation_items_positive_pounds"),
        ),
        sa.ForeignKeyConstraint(
            ["donation_allocation_id"],
            ["donation_allocations.id"],
            name=op.f(
                "fk_donation_allocation_items_donation_allocation_id_donation_allocations"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_category_code"],
            ["food_categories.code"],
            name=op.f(
                "fk_donation_allocation_items_food_category_code_food_categories"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_donation_allocation_items"),
        ),
        sa.UniqueConstraint(
            "donation_allocation_id",
            "food_category_code",
            name="allocation_food_category",
        ),
    )
    op.create_index(
        op.f("ix_donation_allocation_items_donation_allocation_id"),
        "donation_allocation_items",
        ["donation_allocation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_donation_allocation_items_donation_allocation_id"),
        table_name="donation_allocation_items",
    )
    op.drop_table("donation_allocation_items")
    op.drop_index(
        "uq_donation_allocations_active_offer_recipient",
        table_name="donation_allocations",
    )
    op.drop_index(
        op.f("ix_donation_allocations_status"),
        table_name="donation_allocations",
    )
    op.drop_index(
        op.f("ix_donation_allocations_recommendation_run_id"),
        table_name="donation_allocations",
    )
    op.drop_index(
        op.f("ix_donation_allocations_recipient_site_id"),
        table_name="donation_allocations",
    )
    op.drop_index(
        op.f("ix_donation_allocations_donation_offer_id"),
        table_name="donation_allocations",
    )
    op.drop_table("donation_allocations")
