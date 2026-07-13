from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import AssetCategory, AssetStatus, Department, Region
from app.schemas import ApiResponse, AssetRead, success

router = APIRouter(prefix="/assets", tags=["assets"])

Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/search", response_model=ApiResponse[list[AssetRead]])
def search_assets(
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category: AssetCategory | None = None,
    status_filter: Annotated[
        AssetStatus | None,
        Query(alias="status"),
    ] = None,
    region: Region | None = None,
    limit: Limit = 50,
    session: Session = Depends(get_db),
) -> ApiResponse[list[AssetRead]]:
    if q is not None and not q.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="q must contain a non-whitespace character",
        )
    items = services.search_assets(session, q, category, status_filter, region, limit)
    return success(items, count=len(items), limit=limit)


@router.get("/stale", response_model=ApiResponse[list[AssetRead]])
def stale_assets(
    stale_days: Annotated[int, Query(ge=1, le=3650)] = 30,
    category: AssetCategory | None = None,
    status_filter: Annotated[
        AssetStatus | None,
        Query(alias="status"),
    ] = None,
    region: Region | None = None,
    limit: Limit = 50,
    session: Session = Depends(get_db),
) -> ApiResponse[list[AssetRead]]:
    cutoff = datetime.now(UTC) - timedelta(days=stale_days)
    items = services.stale_assets(
        session,
        cutoff=cutoff,
        category=category,
        status=status_filter,
        region=region,
        limit=limit,
    )
    return success(items, count=len(items), limit=limit)


@router.get(
    "/by-department",
    response_model=ApiResponse[list[AssetRead]],
)
def by_department(
    department: Department,
    category: AssetCategory | None = None,
    status_filter: Annotated[
        AssetStatus | None,
        Query(alias="status"),
    ] = None,
    region: Region | None = None,
    stale_days: Annotated[int | None, Query(ge=1, le=3650)] = None,
    limit: Limit = 50,
    session: Session = Depends(get_db),
) -> ApiResponse[list[AssetRead]]:
    cutoff = datetime.now(UTC) - timedelta(days=stale_days) if stale_days is not None else None
    items = services.assets_by_department(
        session,
        department=department,
        category=category,
        status=status_filter,
        region=region,
        cutoff=cutoff,
        limit=limit,
    )
    return success(items, count=len(items), limit=limit)


@router.get("/{asset_id}", response_model=ApiResponse[AssetRead])
def get_asset(
    asset_id: int,
    session: Session = Depends(get_db),
) -> ApiResponse[AssetRead]:
    item = services.get_asset(session, asset_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="asset not found",
        )
    return success(item, count=1)
