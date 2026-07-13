"""SQLAlchemy models: Asset, User, Checkout
Schema decisions (see project_log.md for full reasoning):
- Integer PKs, not UUIDs — easier for an LLM to carry between tool calls
  and to eyeball in a LangSmith trace while debugging.
- `checkouts` is the single source of truth for "who currently has this
  asset" (latest row where checked_in_at IS NULL). `assets` does NOT store
  a redundant `checked_out_to` field — avoids a second source of truth
  that could drift out of sync.
- category / status / region / department are all Postgres enums, not
  free text — reliable filtering, and a closed set the LLM's tool schema
  can enforce rather than guess at.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from db import Base

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
 
 
class Asset(Base):
    __tablename__ = "assets"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    category: Mapped[AssetCategory] = mapped_column(SqlEnum(AssetCategory, name="asset_category"))
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[AssetStatus] = mapped_column(SqlEnum(AssetStatus, name="asset_status"))
    region: Mapped[Region] = mapped_column(SqlEnum(Region, name="region"))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
 
    checkouts: Mapped[list["Checkout"]] = relationship(back_populates="asset")
 
 
class User(Base):
    __tablename__ = "users"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    department: Mapped[Department] = mapped_column(SqlEnum(Department, name="department"))
 
    checkouts: Mapped[list["Checkout"]] = relationship(back_populates="user")
 
 
class Checkout(Base):
    """Single source of truth for asset holder history.
 
    Current holder = the row for a given asset_id with the latest
    checked_out_at where checked_in_at IS NULL. `assets.status` reflects
    simple state (available/checked_out/retired) but never identity.
    """
 
    __tablename__ = "checkouts"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    checked_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
 
    asset: Mapped["Asset"] = relationship(back_populates="checkouts")
    user: Mapped["User"] = relationship(back_populates="checkouts")
 