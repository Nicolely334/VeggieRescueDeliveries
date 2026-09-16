import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.donation_offer import DonationOffer


def test_donation_offer_has_source_tracking_columns() -> None:
    table = DonationOffer.__table__

    assert table.c.source_system.type.length == 100
    assert table.c.source_record_id.type.length == 200
    assert table.c.source_row_fingerprint.type.length == 64

    assert table.c.source_system.nullable is True
    assert table.c.source_record_id.nullable is True
    assert table.c.source_submitted_at.nullable is True
    assert table.c.source_row_fingerprint.nullable is True


def test_donation_offer_source_identity_is_constrained() -> None:
    table = DonationOffer.__table__

    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "donation_offer_source_record" in unique_constraint_names
    assert (
        "ck_donation_offers_complete_source_identity"
        in check_constraint_names
    )


def test_donation_offer_preserves_source_metadata() -> None:
    submitted_at = datetime(
        2026,
        9,
        15,
        18,
        30,
        tzinfo=UTC,
    )
    fingerprint = "a" * 64

    offer = DonationOffer(
        farm_id=uuid.uuid4(),
        source_system="google_sheets_donation_intake",
        source_record_id="response-123",
        source_submitted_at=submitted_at,
        source_row_fingerprint=fingerprint,
        status="open",
    )

    assert offer.source_system == "google_sheets_donation_intake"
    assert offer.source_record_id == "response-123"
    assert offer.source_submitted_at == submitted_at
    assert offer.source_row_fingerprint == fingerprint