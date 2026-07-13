from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ApiResponse, HealthRead, success

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthRead])
def health(
    response: Response,
    session: Session = Depends(get_db),
) -> ApiResponse[HealthRead]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        payload = HealthRead(status="degraded", database="unavailable")
        return success(payload, count=1)
    payload = HealthRead(status="ok", database="ok")
    return success(payload, count=1)
