"""seed roles, permissions, settings, plans, payment card, bootstrap admins

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-31
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.core.config import settings
from app.core.permissions import (
    ALL_PERMISSIONS,
    DEFAULT_SETTINGS,
    PERMISSION_DESCRIPTIONS,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    ROLE_SUPER_ADMIN,
)

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Default catalog matching the spec (prices in Toman; editable from the panel).
DEFAULT_PLANS = [
    ("۱ گیگ / ۳۰ روز", 1, 30, 30000, 10),
    ("۲ گیگ / ۳۰ روز", 2, 30, 55000, 20),
    ("۳ گیگ / ۳۰ روز", 3, 30, 75000, 30),
    ("۵ گیگ / ۳۰ روز", 5, 30, 110000, 40),
    ("۱۰ گیگ / ۳۰ روز", 10, 30, 190000, 50),
    ("۱۵ گیگ / ۳۰ روز", 15, 30, 260000, 60),
]


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    perms = sa.table(
        "permissions", sa.column("id", sa.BigInteger), sa.column("code", sa.String),
        sa.column("description", sa.Text),
    )
    roles = sa.table(
        "roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String),
        sa.column("description", sa.Text), sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    role_perms = sa.table(
        "role_permissions", sa.column("role_id", sa.BigInteger),
        sa.column("permission_id", sa.BigInteger),
    )

    # --- permissions ---
    op.bulk_insert(
        perms,
        [{"code": c, "description": PERMISSION_DESCRIPTIONS[c]} for c in ALL_PERMISSIONS],
    )
    perm_ids = {
        row.code: row.id
        for row in bind.execute(sa.text("SELECT id, code FROM permissions"))
    }

    # --- roles ---
    op.bulk_insert(
        roles,
        [
            {
                "name": name,
                "description": ROLE_DESCRIPTIONS[name],
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            }
            for name in ROLE_PERMISSIONS
        ],
    )
    role_ids = {
        row.name: row.id for row in bind.execute(sa.text("SELECT id, name FROM roles"))
    }

    # --- role_permissions mapping ---
    mappings = [
        {"role_id": role_ids[role], "permission_id": perm_ids[code]}
        for role, codes in ROLE_PERMISSIONS.items()
        for code in codes
    ]
    op.bulk_insert(role_perms, mappings)

    # --- settings ---
    settings_tbl = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", sa.JSON),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        settings_tbl,
        [{"key": k, "value": json.dumps(v), "updated_at": now} for k, v in DEFAULT_SETTINGS.items()],
    )

    # --- default plans (manual fulfilment by default) ---
    plans_tbl = sa.table(
        "plans",
        sa.column("title", sa.String), sa.column("data_limit_gb", sa.Integer),
        sa.column("duration_days", sa.Integer), sa.column("price", sa.BigInteger),
        sa.column("fulfilment_mode", sa.Enum(name="fulfilment_mode")),
        sa.column("is_active", sa.Boolean), sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        plans_tbl,
        [
            {
                "title": title, "data_limit_gb": gb, "duration_days": days,
                "price": price, "fulfilment_mode": "manual", "is_active": True,
                "sort_order": order, "created_at": now, "updated_at": now,
            }
            for (title, gb, days, price, order) in DEFAULT_PLANS
        ],
    )

    # --- bootstrap super admins from BOOTSTRAP_SUPER_ADMINS ---
    super_role_id = role_ids[ROLE_SUPER_ADMIN]
    admins_tbl = sa.table(
        "admin_users",
        sa.column("telegram_id", sa.BigInteger), sa.column("full_name", sa.String),
        sa.column("role_id", sa.BigInteger), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    if settings.bootstrap_admin_ids:
        op.bulk_insert(
            admins_tbl,
            [
                {
                    "telegram_id": tid, "full_name": "Super Admin",
                    "role_id": super_role_id, "is_active": True,
                    "created_at": now, "updated_at": now,
                }
                for tid in settings.bootstrap_admin_ids
            ],
        )


def downgrade() -> None:
    op.execute("DELETE FROM admin_users")
    op.execute("DELETE FROM plans")
    op.execute("DELETE FROM settings")
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM roles")
    op.execute("DELETE FROM permissions")
