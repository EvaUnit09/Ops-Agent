import random
from datetime import timedelta

from app.models import AssetCategory, AssetStatus, Department
from app.seed import (
    ASSET_COUNT,
    BASE_TIME,
    RANDOM_SEED,
    USER_COUNT,
    build_assets,
    build_checkouts,
    build_users,
)


def test_seed_totals_and_marketing_laptop_fixture() -> None:
    rng = random.Random(RANDOM_SEED)
    users = build_users()
    assets = build_assets(rng)
    checkouts = build_checkouts(rng, assets, users)

    assert len(users) == USER_COUNT == 200
    assert len(assets) == ASSET_COUNT == 2_000

    flagship = next(asset for asset in assets if asset.tag == "AST-000001")
    open_checkout = next(
        checkout
        for checkout in checkouts
        if checkout.asset is flagship and checkout.checked_in_at is None
    )
    assert flagship.category is AssetCategory.laptop
    assert flagship.status is AssetStatus.checked_out
    assert flagship.last_synced_at <= BASE_TIME - timedelta(days=30)
    assert open_checkout.user.department is Department.marketing
