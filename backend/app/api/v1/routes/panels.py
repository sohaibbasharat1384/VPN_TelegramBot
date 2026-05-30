"""Panel integration management (Marzban / X-UI). Credentials encrypted at rest."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.exceptions import NotFoundError, ValidationError
from app.core.permissions import Perm
from app.core.security import encrypt_secret
from app.models.catalog import Panel
from app.models.enums import ActorType, PanelType
from app.models.rbac import AdminUser
from app.schemas.models import PanelCreate, PanelRead
from app.services import audit

router = APIRouter(prefix="/panels", tags=["panels"])


@router.get("", response_model=list[PanelRead],
            dependencies=[Depends(require_permission(Perm.PANELS_MANAGE))])
async def list_panels(db: DbSession) -> list[PanelRead]:
    rows = (await db.execute(select(Panel).order_by(Panel.id))).scalars().all()
    return [PanelRead.model_validate(p) for p in rows]


@router.post("", response_model=PanelRead)
async def create_panel(
    payload: PanelCreate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PANELS_MANAGE)),
) -> PanelRead:
    try:
        panel_type = PanelType(payload.type)
    except ValueError as exc:
        raise ValidationError(user_message="نوع پنل نامعتبر است.") from exc
    panel = Panel(
        name=payload.name,
        type=panel_type,
        base_url=payload.base_url,
        username=payload.username,
        password_enc=encrypt_secret(payload.password),
        extra=payload.extra,
        is_active=True,
    )
    db.add(panel)
    await db.flush()
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="panel.create",
        target_type="panel", target_id=panel.id, ip_address=ip,
        new_value={"name": panel.name, "type": panel.type.value},
    )
    await db.commit()
    return PanelRead.model_validate(panel)


@router.post("/{panel_id}/toggle", response_model=PanelRead)
async def toggle_panel(
    panel_id: int, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PANELS_MANAGE)),
) -> PanelRead:
    panel = await db.get(Panel, panel_id)
    if panel is None:
        raise NotFoundError(user_message="پنل یافت نشد.")
    panel.is_active = not panel.is_active
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="panel.toggle",
        target_type="panel", target_id=panel_id, ip_address=ip,
        new_value={"is_active": panel.is_active},
    )
    await db.commit()
    return PanelRead.model_validate(panel)
