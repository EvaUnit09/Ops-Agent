from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Checkout


def test_only_one_open_checkout_per_asset(
    db: Session,
    sample_data: dict[str, int],
) -> None:
    db.add(
        Checkout(
            asset_id=sample_data["checked_out_asset_id"],
            user_id=sample_data["marketer_id"],
            checked_out_at=datetime.now(UTC),
            checked_in_at=None,
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_check_in_cannot_precede_check_out(
    db: Session,
    sample_data: dict[str, int],
) -> None:
    checked_out_at = datetime.now(UTC)
    db.add(
        Checkout(
            asset_id=sample_data["available_asset_id"],
            user_id=sample_data["engineer_id"],
            checked_out_at=checked_out_at,
            checked_in_at=checked_out_at - timedelta(seconds=1),
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
