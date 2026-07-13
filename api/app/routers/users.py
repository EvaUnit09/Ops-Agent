from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import Department
from app.schemas import ApiResponse, UserRead, success

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=ApiResponse[list[UserRead]])
def search_users(
    department: Department,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    session: Session = Depends(get_db),
) -> ApiResponse[list[UserRead]]:
    if q is not None and not q.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="q must contain a non-whitespace character",
        )
    items = services.search_users(
        session,
        department=department,
        query=q,
        limit=limit,
    )
    return success(items, count=len(items), limit=limit)
