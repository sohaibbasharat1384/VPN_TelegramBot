"""Authentication endpoints: login, refresh, logout, profile."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.v1.deps import ClientIP, CurrentAdmin, DbSession
from app.schemas.auth import AdminProfile, LoginRequest, RefreshRequest, TokenPair
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, request: Request, db: DbSession, ip: ClientIP) -> TokenPair:
    return await auth_service.login(
        db,
        payload.email,
        payload.password,
        user_agent=request.headers.get("user-agent"),
        ip=ip,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest, request: Request, db: DbSession, ip: ClientIP
) -> TokenPair:
    return await auth_service.refresh(
        db,
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip=ip,
    )


@router.post("/logout", status_code=204, response_class=Response)
async def logout(payload: RefreshRequest, db: DbSession) -> Response:
    await auth_service.revoke_refresh_token(db, payload.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=AdminProfile)
async def me(admin: CurrentAdmin) -> AdminProfile:
    return AdminProfile(
        id=admin.id,
        email=admin.email,
        telegram_id=admin.telegram_id,
        full_name=admin.full_name,
        role=admin.role.name,
        permissions=admin.permission_codes,
        is_active=admin.is_active,
    )
