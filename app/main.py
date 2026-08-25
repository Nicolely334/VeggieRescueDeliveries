from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.recipient_sites import router as recipient_sites_router
from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()
DatabaseSession = Annotated[Session, Depends(get_db)]

app = FastAPI(
    title=settings.app_name,
    description="Equitable food rescue delivery recommendation system.",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(
    recipient_sites_router,
    prefix="/api/v1",
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_environment,
    }


@app.get("/health/database", tags=["system"])
def database_health_check(db: DatabaseSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {"status": "ok"}
