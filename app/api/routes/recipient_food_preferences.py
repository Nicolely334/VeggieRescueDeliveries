import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.food_category import FoodCategory
from app.models.recipient_food_preference import (
    RecipientFoodPreference,
)
from app.models.recipient_site import RecipientSite
from app.schemas.food_preference import (
    RecipientFoodPreferenceRead,
    RecipientFoodPreferencesRead,
    RecipientFoodPreferencesReplace,
)

router = APIRouter(
    prefix="/recipient-sites",
    tags=["recipient food preferences"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def build_preferences_read(
    recipient: RecipientSite,
    preference_rows: Sequence[tuple[RecipientFoodPreference, str]],
) -> RecipientFoodPreferencesRead:
    preferences = [
        RecipientFoodPreferenceRead(
            id=preference.id,
            food_category_code=(preference.food_category_code),
            category_name=category_name,
            maximum_pounds=(
                float(preference.maximum_pounds) if preference.maximum_pounds is not None else None
            ),
            notes=preference.notes,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )
        for preference, category_name in preference_rows
    ]

    return RecipientFoodPreferencesRead(
        recipient_site_id=recipient.id,
        recipient_name=recipient.name,
        preferences=preferences,
    )


def load_preferences_read(
    db: Session,
    recipient_site_id: uuid.UUID,
) -> RecipientFoodPreferencesRead | None:
    recipient = db.get(
        RecipientSite,
        recipient_site_id,
    )

    if recipient is None:
        return None

    preference_rows = db.execute(
        select(
            RecipientFoodPreference,
            FoodCategory.name.label("category_name"),
        )
        .join(
            FoodCategory,
            FoodCategory.code == RecipientFoodPreference.food_category_code,
        )
        .where(RecipientFoodPreference.recipient_site_id == recipient_site_id)
        .order_by(FoodCategory.name)
    ).all()

    return build_preferences_read(
        recipient=recipient,
        preference_rows=preference_rows,
    )


@router.get(
    "/{recipient_site_id}/food-preferences",
    response_model=RecipientFoodPreferencesRead,
)
def get_recipient_food_preferences(
    recipient_site_id: uuid.UUID,
    db: DatabaseSession,
) -> RecipientFoodPreferencesRead:
    preferences = load_preferences_read(
        db=db,
        recipient_site_id=recipient_site_id,
    )

    if preferences is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recipient site not found",
        )

    return preferences


@router.put(
    "/{recipient_site_id}/food-preferences",
    response_model=RecipientFoodPreferencesRead,
)
def replace_recipient_food_preferences(
    recipient_site_id: uuid.UUID,
    preference_data: RecipientFoodPreferencesReplace,
    db: DatabaseSession,
) -> RecipientFoodPreferencesRead:
    recipient = db.get(
        RecipientSite,
        recipient_site_id,
    )

    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recipient site not found",
        )

    category_codes = {item.food_category_code for item in preference_data.items}

    active_category_codes: set[str] = set()

    if category_codes:
        active_category_codes = set(
            db.scalars(
                select(FoodCategory.code).where(
                    FoodCategory.code.in_(category_codes),
                    FoodCategory.is_active.is_(True),
                )
            ).all()
        )

    unavailable_codes = sorted(category_codes - active_category_codes)

    if unavailable_codes:
        raise HTTPException(
            status_code=422,
            detail={
                "message": ("one or more food categories are unavailable"),
                "food_category_codes": unavailable_codes,
            },
        )

    try:
        db.execute(
            delete(RecipientFoodPreference).where(
                RecipientFoodPreference.recipient_site_id == recipient_site_id
            )
        )

        db.add_all(
            [
                RecipientFoodPreference(
                    recipient_site_id=recipient_site_id,
                    food_category_code=(item.food_category_code),
                    maximum_pounds=(
                        Decimal(str(item.maximum_pounds))
                        if item.maximum_pounds is not None
                        else None
                    ),
                    notes=item.notes,
                )
                for item in preference_data.items
            ]
        )

        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("recipient food preferences could not be saved"),
        ) from error

    saved_preferences = load_preferences_read(
        db=db,
        recipient_site_id=recipient_site_id,
    )

    if saved_preferences is None:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=("saved food preferences could not be loaded"),
        )

    return saved_preferences
