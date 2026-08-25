from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recipient_site import RecipientSite
from app.schemas.recipient_site import (
    RecipientSiteCreate,
    RecipientSiteRead,
)

router = APIRouter(
    prefix="/recipient-sites",
    tags=["recipient sites"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=RecipientSiteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recipient_site(
    recipient_data: RecipientSiteCreate,
    db: DatabaseSession,
) -> RecipientSite:
    recipient_site = RecipientSite(**recipient_data.model_dump())

    db.add(recipient_site)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="recipient site could not be created",
        ) from error

    db.refresh(recipient_site)
    return recipient_site


@router.get(
    "",
    response_model=list[RecipientSiteRead],
)
def list_recipient_sites(
    db: DatabaseSession,
    include_inactive: bool = False,
) -> Sequence[RecipientSite]:
    statement = select(RecipientSite).order_by(RecipientSite.name)

    if not include_inactive:
        statement = statement.where(RecipientSite.is_active.is_(True))

    return db.scalars(statement).all()
