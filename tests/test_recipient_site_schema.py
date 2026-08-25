import pytest
from pydantic import ValidationError

from app.schemas.recipient_site import RecipientSiteCreate


def test_recipient_site_accepts_valid_priority() -> None:
    recipient = RecipientSiteCreate(
        name="Community Food Pantry",
        priority=1,
    )

    assert recipient.name == "Community Food Pantry"
    assert recipient.priority == 1


def test_recipient_site_strips_name_whitespace() -> None:
    recipient = RecipientSiteCreate(
        name="  Community Food Pantry  ",
        priority=2,
    )

    assert recipient.name == "Community Food Pantry"


def test_recipient_site_rejects_invalid_priority() -> None:
    with pytest.raises(ValidationError):
        RecipientSiteCreate(
            name="Community Food Pantry",
            priority=6,
        )


def test_recipient_site_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        RecipientSiteCreate(
            name="   ",
            priority=1,
        )
