import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://ops_agent:ops_agent@localhost:5432/ops_agent_test",
)
if not make_url(TEST_DATABASE_URL).database.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL database name must end in '_test'")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Asset,
    AssetCategory,
    AssetStatus,
    Checkout,
    Department,
    Region,
    User,
)

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSession = sessionmaker(
    bind=test_engine,
    class_=Session,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Generator[None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None]:
    yield
    with TestSession.begin() as session:
        session.execute(delete(Checkout))
        session.execute(delete(Asset))
        session.execute(delete(User))


@pytest.fixture
def db() -> Generator[Session]:
    with TestSession() as session:
        yield session


@pytest.fixture
def client() -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db: Session) -> dict[str, int]:
    now = datetime.now(UTC)
    engineer = User(
        name="Ada Engineer",
        email="ada@example.com",
        department=Department.engineering,
    )
    marketer = User(
        name="Morgan Marketer",
        email="morgan@example.com",
        department=Department.marketing,
    )
    checked_out = Asset(
        tag="AST-000002",
        category=AssetCategory.laptop,
        model="ThinkPad T14",
        status=AssetStatus.checked_out,
        region=Region.us_east,
        last_synced_at=now - timedelta(days=100),
    )
    available = Asset(
        tag="AST-000001",
        category=AssetCategory.monitor,
        model="UltraSharp",
        status=AssetStatus.available,
        region=Region.emea,
        last_synced_at=now - timedelta(days=1),
    )
    db.add_all([engineer, marketer, checked_out, available])
    db.flush()
    old_checkout = Checkout(
        asset=checked_out,
        user=marketer,
        checked_out_at=now - timedelta(days=60),
        checked_in_at=now - timedelta(days=50),
    )
    open_checkout = Checkout(
        asset=checked_out,
        user=engineer,
        checked_out_at=now - timedelta(days=20),
        checked_in_at=None,
    )
    db.add_all([old_checkout, open_checkout])
    db.commit()
    return {
        "engineer_id": engineer.id,
        "marketer_id": marketer.id,
        "checked_out_asset_id": checked_out.id,
        "available_asset_id": available.id,
        "open_checkout_id": open_checkout.id,
    }
