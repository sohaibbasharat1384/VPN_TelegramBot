"""Authentication service: login, token issuance, rotating refresh tokens."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import PermissionDeniedError
from app.models.rbac import AdminUser, RefreshToken
from app.schemas.auth import TokenPair


async def get_admin_by_id(db: AsyncSession, admin_id: int) -> AdminUser | None:
    return await db.get(AdminUser, admin_id)


async def authenticate(db: AsyncSession, email: str, password: str) -> AdminUser:
    stmt = select(AdminUser).where(AdminUser.email == email)
    admin = (await db.execute(stmt)).scalar_one_or_none()
    if (
        admin is None
        or not admin.is_active
        or not admin.hashed_password
        or not security.verify_password(password, admin.hashed_password)
    ):
        # Uniform error — never reveal which factor failed.
        raise PermissionDeniedError(user_message="ایمیل یا رمز عبور نادرست است.")
    return admin


async def _issue_pair(
    db: AsyncSession, admin: AdminUser, *, user_agent: str | None, ip: str | None
) -> TokenPair:
    access = security.create_access_token(
        admin.id, role=admin.role.name, permissions=admin.permission_codes
    )
    raw_refresh = security.generate_refresh_token()
    db.add(
        RefreshToken(
            admin_user_id=admin.id,
            token_hash=security.hash_token(raw_refresh),
            expires_at=security.refresh_token_expiry(),
            user_agent=(user_agent or "")[:512] or None,
            ip_address=ip,
        )
    )
    await db.flush()
    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def login(
    db: AsyncSession, email: str, password: str, *, user_agent: str | None, ip: str | None
) -> TokenPair:
    admin = await authenticate(db, email, password)
    admin.last_login_at = datetime.now(UTC)
    pair = await _issue_pair(db, admin, user_agent=user_agent, ip=ip)
    await db.commit()
    return pair


async def refresh(
    db: AsyncSession, raw_refresh: str, *, user_agent: str | None, ip: str | None
) -> TokenPair:
    token_hash = security.hash_token(raw_refresh)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    token = (await db.execute(stmt)).scalar_one_or_none()

    now = datetime.now(UTC)
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        raise PermissionDeniedError(user_message="نشست شما منقضی شده است. دوباره وارد شوید.")

    admin = await db.get(AdminUser, token.admin_user_id)
    if admin is None or not admin.is_active:
        raise PermissionDeniedError(user_message="حساب کاربری غیرفعال است.")

    # Rotate: issue a new pair, then revoke and link the old one.
    pair = await _issue_pair(db, admin, user_agent=user_agent, ip=ip)
    new_token = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == security.hash_token(pair.refresh_token)
            )
        )
    ).scalar_one()
    token.revoked_at = now
    token.replaced_by_id = new_token.id
    await db.commit()
    return pair


async def revoke_refresh_token(db: AsyncSession, raw_refresh: str) -> None:
    token_hash = security.hash_token(raw_refresh)
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if token and token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        await db.commit()
