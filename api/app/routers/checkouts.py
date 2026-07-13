from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.schemas import ApiResponse, AssetRead, CheckoutRead, success

router = APIRouter(prefix="/checkouts", tags=["checkouts"])


@router.get(
    "/asset/{asset_id}",
    response_model=ApiResponse[list[CheckoutRead]],
)
def for_asset(
    asset_id: int,
    session: Session = Depends(get_db),
) -> ApiResponse[list[CheckoutRead]]:
    if not services.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="asset not found",
        )
    items = services.checkouts_for_asset(session, asset_id=asset_id)
    return success(items, count=len(items))


@router.get(
    "/user/{user_id}",
    response_model=ApiResponse[list[AssetRead]],
)
def for_user(
    user_id: int,
    session: Session = Depends(get_db),
) -> ApiResponse[list[AssetRead]]:
    if not services.user_exists(session, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    items = services.current_assets_for_user(session, user_id=user_id)
    return success(items, count=len(items))
