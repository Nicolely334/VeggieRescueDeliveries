from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.food_category import FoodCategory
from app.schemas.food_preference import FoodCategoryRead

router = APIRouter(
    prefix="/food-categories",
    tags=["food categories"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[FoodCategoryRead],
)
def list_food_categories(
    db: DatabaseSession,
    include_inactive: bool = False,
) -> Sequence[FoodCategory]:
    statement = select(FoodCategory).order_by(FoodCategory.name)

    if not include_inactive:
        statement = statement.where(FoodCategory.is_active.is_(True))

    return db.scalars(statement).all()
