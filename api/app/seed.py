import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text

from app.database import SessionLocal
from app.models import (
    Asset,
    AssetCategory,
    AssetStatus,
    Checkout,
    Department,
    Region,
    User,
)

RANDOM_SEED = 20260710
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
USER_COUNT = 200
ASSET_COUNT = 2_000

FIRST_NAMES = (
    "Alex",
    "Blair",
    "Casey",
    "Drew",
    "Emery",
    "Frankie",
    "Gray",
    "Harper",
    "Indigo",
    "Jordan",
)
LAST_NAMES = (
    "Adams",
    "Baker",
    "Chen",
    "Diaz",
    "Evans",
    "Foster",
    "Garcia",
    "Hughes",
    "Ivanov",
    "Jones",
)
MODELS = {
    AssetCategory.laptop: ("ThinkPad T14", "MacBook Pro 14", "Latitude 7440"),
    AssetCategory.monitor: ("UltraSharp U2723QE", "ThinkVision P27h"),
    AssetCategory.phone: ("iPhone 15", "Pixel 9", "Galaxy S25"),
    AssetCategory.desktop: ("OptiPlex 7020", "Mac mini M4"),
    AssetCategory.tablet: ("iPad Air", "Surface Pro 11"),
}


def build_users() -> list[User]:
    departments = list(Department)
    users: list[User] = []
    for number in range(1, USER_COUNT + 1):
        first = FIRST_NAMES[(number - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[((number - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
        users.append(
            User(
                name=f"{first} {last} {number:03d}",
                email=f"user{number:03d}@example.com",
                department=departments[(number - 1) % len(departments)],
            )
        )
    return users


def build_assets(rng: random.Random) -> list[Asset]:
    categories = list(AssetCategory)
    regions = list(Region)
    statuses = (
        AssetStatus.available,
        AssetStatus.checked_out,
        AssetStatus.retired,
    )
    assets: list[Asset] = []
    for number in range(1, ASSET_COUNT + 1):
        category = categories[(number - 1) % len(categories)]
        status = rng.choices(statuses, weights=(55, 35, 10), k=1)[0]
        assets.append(
            Asset(
                tag=f"AST-{number:06d}",
                category=category,
                model=rng.choice(MODELS[category]),
                status=status,
                region=regions[(number - 1) % len(regions)],
                last_synced_at=BASE_TIME
                - timedelta(
                    days=rng.randint(0, 120),
                    minutes=rng.randint(0, 1_439),
                ),
            )
        )
    flagship = assets[0]
    flagship.category = AssetCategory.laptop
    flagship.model = "ThinkPad T14"
    flagship.status = AssetStatus.checked_out
    flagship.region = Region.emea
    flagship.last_synced_at = BASE_TIME - timedelta(days=45)
    return assets


def build_checkouts(
    rng: random.Random,
    assets: list[Asset],
    users: list[User],
) -> list[Checkout]:
    checkouts: list[Checkout] = []
    marketing_user = next(user for user in users if user.department is Department.marketing)
    for asset in assets:
        if asset.status is AssetStatus.checked_out:
            checked_out_at = BASE_TIME - timedelta(
                days=rng.randint(0, 90),
                minutes=rng.randint(0, 1_439),
            )
            checkouts.append(
                Checkout(
                    asset=asset,
                    user=(marketing_user if asset.tag == "AST-000001" else rng.choice(users)),
                    checked_out_at=checked_out_at,
                    checked_in_at=None,
                )
            )
        elif rng.random() < 0.30:
            checked_out_at = BASE_TIME - timedelta(
                days=rng.randint(31, 365),
                minutes=rng.randint(0, 1_439),
            )
            checkouts.append(
                Checkout(
                    asset=asset,
                    user=rng.choice(users),
                    checked_out_at=checked_out_at,
                    checked_in_at=checked_out_at + timedelta(days=rng.randint(1, 30)),
                )
            )
    return checkouts


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    users = build_users()
    assets = build_assets(rng)
    checkouts = build_checkouts(rng, assets, users)

    with SessionLocal.begin() as session:
        session.execute(text("TRUNCATE TABLE checkouts, assets, users RESTART IDENTITY CASCADE"))
        session.add_all(users)
        session.add_all(assets)
        session.add_all(checkouts)
        session.flush()

        open_count = session.scalar(
            select(func.count()).select_from(Checkout).where(Checkout.checked_in_at.is_(None))
        )
        checked_out_count = session.scalar(
            select(func.count()).select_from(Asset).where(Asset.status == AssetStatus.checked_out)
        )
        if open_count != checked_out_count:
            raise RuntimeError(
                "seed invariant failed: checked-out assets and open checkouts differ"
            )

        flagship_count = session.scalar(
            select(func.count())
            .select_from(Asset)
            .join(
                Checkout,
                (Checkout.asset_id == Asset.id) & Checkout.checked_in_at.is_(None),
            )
            .join(User, User.id == Checkout.user_id)
            .where(
                User.department == Department.marketing,
                Asset.category == AssetCategory.laptop,
                Asset.last_synced_at <= BASE_TIME - timedelta(days=30),
            )
        )
        if not flagship_count:
            raise RuntimeError("seed invariant failed: no stale Marketing laptop")

    print(
        f"Seeded {len(assets)} assets, {len(users)} users, "
        f"and {len(checkouts)} checkouts with seed {RANDOM_SEED}."
    )


if __name__ == "__main__":
    main()
