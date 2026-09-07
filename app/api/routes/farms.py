from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmRead

router = APIRouter(
    prefix="/farms",
    tags=["farms"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=FarmRead,
    status_code=status.HTTP_201_CREATED,
)
def create_farm(
    farm_data: FarmCreate,
    db: DatabaseSession,
) -> Farm:
    farm = Farm(**farm_data.model_dump())
    db.add(farm)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a farm with this name already exists",
        ) from error

    db.refresh(farm)
    return farm


@router.get(
    "",
    response_model=list[FarmRead],
)
def list_farms(
    db: DatabaseSession,
    include_inactive: bool = False,
) -> Sequence[Farm]:
    statement = select(Farm).order_by(Farm.name)

    if not include_inactive:
        statement = statement.where(Farm.is_active.is_(True))

    return db.scalars(statement).all()
