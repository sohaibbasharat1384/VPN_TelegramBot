"""Audit logging — records every mutating admin/system action.

Per the spec: nothing should happen without logging. Mutating service functions
call ``record`` with actor, action, target, and old/new values.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType
from app.models.system import AuditLog


def _jsonable(value: Any) -> Any:
    """Coerce arbitrary values into a JSON-serializable form for storage."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


async def record(
    db: AsyncSession,
    *,
    action: str,
    actor_type: ActorType = ActorType.admin,
    actor_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    ip_address: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit entry. Caller owns the surrounding transaction."""
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        old_value=_jsonable(old_value) if old_value is not None else None,
        new_value=_jsonable(new_value) if new_value is not None else None,
    )
    db.add(entry)
    await db.flush()
    return entry
