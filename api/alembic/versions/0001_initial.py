"""Create users, assets, and checkout history.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


asset_category = postgresql.ENUM(
    "laptop",
    "monitor",
    "phone",
    "desktop",
    "tablet",
    name="asset_category",
)
asset_status = postgresql.ENUM(
    "available",
    "checked_out",
    "retired",
    name="asset_status",
)
region = postgresql.ENUM(
    "us-east",
    "us-west",
    "emea",
    "apac",
    name="region",
)
department = postgresql.ENUM(
    "Engineering",
    "Marketing",
    "Sales",
    "Finance",
    "IT",
    "HR",
    "Operations",
    name="department",
)


def upgrade() -> None:
    bind = op.get_bind()
    asset_category.create(bind, checkfirst=False)
    asset_status.create(bind, checkfirst=False)
    region.create(bind, checkfirst=False)
    department.create(bind, checkfirst=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=20), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                name="asset_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                name="asset_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "region",
            postgresql.ENUM(name="region", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(tag)) > 0",
            name="ck_assets_tag_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(model)) > 0",
            name="ck_assets_model_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tag"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "department",
            postgresql.ENUM(
                name="department",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_users_name_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(email)) > 0",
            name="ck_users_email_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "checkouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "checked_out_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "checked_in_at IS NULL OR checked_in_at >= checked_out_at",
            name="ck_checkouts_valid_time_range",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_checkouts_asset_id",
        "checkouts",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_checkouts_user_id",
        "checkouts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_checkouts_one_open_per_asset",
        "checkouts",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text("checked_in_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_checkouts_one_open_per_asset",
        table_name="checkouts",
        postgresql_where=sa.text("checked_in_at IS NULL"),
    )
    op.drop_index("ix_checkouts_user_id", table_name="checkouts")
    op.drop_index("ix_checkouts_asset_id", table_name="checkouts")
    op.drop_table("checkouts")
    op.drop_table("users")
    op.drop_table("assets")

    bind = op.get_bind()
    department.drop(bind, checkfirst=False)
    region.drop(bind, checkfirst=False)
    asset_status.drop(bind, checkfirst=False)
    asset_category.drop(bind, checkfirst=False)
