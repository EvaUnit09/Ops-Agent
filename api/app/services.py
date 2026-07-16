from datetime import datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    AssetCategory,
    AssetStatus,
    Checkout,
    Department,
    Region,
    User,
)
from app.schemas import (
    AssetRead,
    AssetSummary,
    CheckoutRead,
    UserRead,
    UserSummary,
)


def _asset_with_holder_statement() -> Select[tuple[Asset, Checkout, User]]:
    return (
        select(Asset, Checkout, User)
        .outerjoin(
            Checkout,
            and_(
                Checkout.asset_id == Asset.id,
                Checkout.checked_in_at.is_(None),
            ),
        )
        .outerjoin(User, User.id == Checkout.user_id)
    )


def _asset_read(row: object) -> AssetRead:
    asset, checkout, user = row
    holder = UserSummary.model_validate(user) if checkout is not None else None
    return AssetRead(
        id=asset.id,
        tag=asset.tag,
        category=asset.category,
        model=asset.model,
        status=asset.status,
        region=asset.region,
        last_synced_at=asset.last_synced_at,
        current_holder=holder,
    )


def _checkout_read(
    checkout: Checkout,
    asset: Asset,
    user: User,
) -> CheckoutRead:
    return CheckoutRead(
        id=checkout.id,
        asset=AssetSummary.model_validate(asset),
        user=UserSummary.model_validate(user),
        checked_out_at=checkout.checked_out_at,
        checked_in_at=checkout.checked_in_at,
    )


def search_assets(
    session: Session,
    category: AssetCategory | None,
    status: AssetStatus | None,
    region: Region | None,
    limit: int,
) -> list[AssetRead]:
    statement = _asset_with_holder_statement()
    if category is not None:
        statement = statement.where(Asset.category == category)
    if status is not None:
        statement = statement.where(Asset.status == status)
    if region is not None:
        statement = statement.where(Asset.region == region)
    statement = statement.order_by(Asset.id.asc()).limit(limit)
    return [_asset_read(row) for row in session.execute(statement)]


def stale_assets(
    session: Session,
    *,
    cutoff: datetime,
    category: AssetCategory | None,
    status: AssetStatus | None,
    region: Region | None,
    limit: int,
) -> list[AssetRead]:
    statement = _asset_with_holder_statement().where(Asset.last_synced_at <= cutoff)
    if category is not None:
        statement = statement.where(Asset.category == category)
    if status is not None:
        statement = statement.where(Asset.status == status)
    if region is not None:
        statement = statement.where(Asset.region == region)
    statement = statement.order_by(Asset.id.asc()).limit(limit)
    return [_asset_read(row) for row in session.execute(statement)]


def assets_by_department(
    session: Session,
    *,
    department: Department,
    category: AssetCategory | None,
    status: AssetStatus | None,
    region: Region | None,
    cutoff: datetime | None,
    limit: int,
) -> list[AssetRead]:
    statement = (
        select(Asset, Checkout, User)
        .join(
            Checkout,
            and_(
                Checkout.asset_id == Asset.id,
                Checkout.checked_in_at.is_(None),
            ),
        )
        .join(User, User.id == Checkout.user_id)
        .where(User.department == department)
    )
    if category is not None:
        statement = statement.where(Asset.category == category)
    if status is not None:
        statement = statement.where(Asset.status == status)
    if region is not None:
        statement = statement.where(Asset.region == region)
    if cutoff is not None:
        statement = statement.where(Asset.last_synced_at <= cutoff)
    statement = statement.order_by(Asset.id.asc()).limit(limit)
    return [_asset_read(row) for row in session.execute(statement)]


def get_asset(session: Session, asset_id: int) -> AssetRead | None:
    row = session.execute(_asset_with_holder_statement().where(Asset.id == asset_id)).one_or_none()
    return _asset_read(row) if row is not None else None


def asset_exists(session: Session, asset_id: int) -> bool:
    return session.scalar(select(Asset.id).where(Asset.id == asset_id)) is not None


def user_exists(session: Session, user_id: int) -> bool:
    return session.scalar(select(User.id).where(User.id == user_id)) is not None


def checkouts_for_asset(
    session: Session,
    *,
    asset_id: int,
) -> list[CheckoutRead]:
    statement = (
        select(Checkout, Asset, User)
        .join(Asset, Asset.id == Checkout.asset_id)
        .join(User, User.id == Checkout.user_id)
        .where(Checkout.asset_id == asset_id)
        .order_by(
            Checkout.checked_out_at.desc(),
            Checkout.id.desc(),
        )
    )
    return [
        _checkout_read(checkout, asset, user)
        for checkout, asset, user in session.execute(statement)
    ]


def current_assets_for_user(
    session: Session,
    *,
    user_id: int,
) -> list[AssetRead]:
    statement = (
        select(Asset, Checkout, User)
        .join(Checkout, Checkout.asset_id == Asset.id)
        .join(User, User.id == Checkout.user_id)
        .where(
            Checkout.user_id == user_id,
            Checkout.checked_in_at.is_(None),
        )
        .order_by(Asset.id.asc())
    )
    return [_asset_read(row) for row in session.execute(statement)]


def search_users(
    session: Session,
    *,
    department: Department,
    query: str | None,
    limit: int,
) -> list[UserRead]:
    statement = select(User).where(User.department == department)
    if query is not None:
        needle = query.strip().lower()
        statement = statement.where(
            or_(
                func.strpos(func.lower(User.name), needle) > 0,
                func.strpos(func.lower(User.email), needle) > 0,
            )
        )
    statement = statement.order_by(User.name.asc(), User.id.asc()).limit(limit)
    return [UserRead.model_validate(user) for user in session.scalars(statement)]
