import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetCategory(str, enum.Enum):
    laptop = "laptop"
    monitor = "monitor"
    phone = "phone"
    desktop = "desktop"
    tablet = "tablet"


class AssetStatus(str, enum.Enum):
    available = "available"
    checked_out = "checked_out"
    retired = "retired"


class Region(str, enum.Enum):
    us_east = "us-east"
    us_west = "us-west"
    emea = "emea"
    apac = "apac"


class Department(str, enum.Enum):
    engineering = "Engineering"
    marketing = "Marketing"
    sales = "Sales"
    finance = "Finance"
    it = "IT"
    hr = "HR"
    operations = "Operations"


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_class]


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "length(trim(tag)) > 0",
            name="ck_assets_tag_not_blank",
        ),
        CheckConstraint(
            "length(trim(model)) > 0",
            name="ck_assets_model_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(20), unique=True)
    category: Mapped[AssetCategory] = mapped_column(
        SQLEnum(
            AssetCategory,
            name="asset_category",
            values_callable=enum_values,
        )
    )
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[AssetStatus] = mapped_column(
        SQLEnum(
            AssetStatus,
            name="asset_status",
            values_callable=enum_values,
        )
    )
    region: Mapped[Region] = mapped_column(
        SQLEnum(
            Region,
            name="region",
            values_callable=enum_values,
        )
    )
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    checkouts: Mapped[list["Checkout"]] = relationship(back_populates="asset")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_users_name_not_blank",
        ),
        CheckConstraint(
            "length(trim(email)) > 0",
            name="ck_users_email_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    department: Mapped[Department] = mapped_column(
        SQLEnum(
            Department,
            name="department",
            values_callable=enum_values,
        )
    )

    checkouts: Mapped[list["Checkout"]] = relationship(back_populates="user")


class Checkout(Base):
    __tablename__ = "checkouts"
    __table_args__ = (
        CheckConstraint(
            "checked_in_at IS NULL OR checked_in_at >= checked_out_at",
            name="ck_checkouts_valid_time_range",
        ),
        Index("ix_checkouts_asset_id", "asset_id"),
        Index("ix_checkouts_user_id", "user_id"),
        Index(
            "uq_checkouts_one_open_per_asset",
            "asset_id",
            unique=True,
            postgresql_where=text("checked_in_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    checked_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    asset: Mapped[Asset] = relationship(back_populates="checkouts")
    user: Mapped[User] = relationship(back_populates="checkouts")
