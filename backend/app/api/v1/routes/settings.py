"""Application settings endpoints (pricing knobs, toggles, thresholds)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.schemas.models import SettingUpdate
from app.services import audit, settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", dependencies=[Depends(require_permission(Perm.SETTINGS_MANAGE))])
async def get_settings(db: DbSession) -> dict:
    return await settings_service.get_all(db)


@router.put("")
async def update_setting(
    payload: SettingUpdate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.SETTINGS_MANAGE)),
) -> dict:
    old = await settings_service.get(db, payload.key)
    await settings_service.set_value(db, payload.key, payload.value, admin_id=admin.id)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="setting.update",
        target_type="setting", ip_address=ip,
        old_value={payload.key: old}, new_value={payload.key: payload.value},
    )
    await db.commit()
    return {"key": payload.key, "value": payload.value}
