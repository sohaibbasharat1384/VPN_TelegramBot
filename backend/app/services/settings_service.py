"""Typed access to the key/value `settings` table (editable from the dashboard)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import DEFAULT_SETTINGS
from app.models.system import Setting


async def get(db: AsyncSession, key: str, default: Any = None) -> Any:
    row = await db.get(Setting, key)
    if row is None:
        return DEFAULT_SETTINGS.get(key, default)
    return row.value


async def get_int(db: AsyncSession, key: str, default: int = 0) -> int:
    return int(await get(db, key, default))


async def get_bool(db: AsyncSession, key: str, default: bool = False) -> bool:
    return bool(await get(db, key, default))


async def get_all(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.execute(select(Setting))).scalars().all()
    merged: dict[str, Any] = dict(DEFAULT_SETTINGS)
    merged.update({r.key: r.value for r in rows})
    return merged


async def set_value(db: AsyncSession, key: str, value: Any, *, admin_id: int | None = None) -> None:
    """Upsert a setting value (caller owns the transaction)."""
    stmt = (
        pg_insert(Setting)
        .values(key=key, value=value, updated_by_id=admin_id)
        .on_conflict_do_update(
            index_elements=[Setting.key],
            set_={"value": value, "updated_by_id": admin_id},
        )
    )
    await db.execute(stmt)
