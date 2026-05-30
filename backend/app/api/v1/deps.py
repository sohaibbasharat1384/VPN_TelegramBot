"""FastAPI dependencies: DB session, current admin, RBAC guards, client IP."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.exceptions import PermissionDeniedError
from app.db.session import get_db
from app.models.rbac import AdminUser
from app.services import auth as auth_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def client_ip(request: Request) -> str | None:
    """Best-effort client IP, honoring a single proxy hop (X-Forwarded-For)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


ClientIP = Annotated[str | None, Depends(client_ip)]


async def get_current_admin(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AdminUser:
    if credentials is None:
        raise PermissionDeniedError(user_message="احراز هویت لازم است.")
    try:
        payload = security.decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise PermissionDeniedError(user_message="توکن نامعتبر است.") from exc

    admin = await auth_service.get_admin_by_id(db, int(payload["sub"]))
    if admin is None or not admin.is_active:
        raise PermissionDeniedError(user_message="حساب کاربری غیرفعال است.")
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


def require_permission(
    *required: str,
) -> Callable[[AdminUser], Coroutine[Any, Any, AdminUser]]:
    """Dependency factory enforcing that the current admin holds all `required`
    permission codes (fetched live from the DB, not just the token)."""

    async def _guard(admin: CurrentAdmin) -> AdminUser:
        held = set(admin.permission_codes)
        missing = [p for p in required if p not in held]
        if missing:
            raise PermissionDeniedError(
                user_message="شما مجاز به انجام این عمل نیستید.",
            )
        return admin

    return _guard
