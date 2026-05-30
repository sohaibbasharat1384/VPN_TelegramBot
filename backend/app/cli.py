"""Management CLI.

Usage (inside the api container):
    python -m app.cli create-admin --email a@b.c --password 'secret' --role super_admin --name "Owner"
    python -m app.cli set-password --email a@b.c --password 'newsecret'
    python -m app.cli list-admins
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core import security
from app.core.permissions import ROLE_PERMISSIONS
from app.db.session import session_scope
from app.models.rbac import AdminUser, Role


async def _create_admin(email: str, password: str, role_name: str, name: str) -> None:
    if role_name not in ROLE_PERMISSIONS:
        raise SystemExit(f"Unknown role '{role_name}'. Valid: {', '.join(ROLE_PERMISSIONS)}")
    async with session_scope() as db:
        role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if role is None:
            raise SystemExit("Roles are not seeded yet. Run `alembic upgrade head` first.")
        existing = (
            await db.execute(select(AdminUser).where(AdminUser.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            raise SystemExit(f"Admin with email {email} already exists.")
        db.add(
            AdminUser(
                email=email,
                full_name=name,
                hashed_password=security.hash_password(password),
                role_id=role.id,
                is_active=True,
            )
        )
    print(f"Created admin {email} with role {role_name}.")


async def _set_password(email: str, password: str) -> None:
    async with session_scope() as db:
        admin = (
            await db.execute(select(AdminUser).where(AdminUser.email == email))
        ).scalar_one_or_none()
        if admin is None:
            raise SystemExit(f"No admin with email {email}.")
        admin.hashed_password = security.hash_password(password)
    print(f"Password updated for {email}.")


async def _list_admins() -> None:
    async with session_scope() as db:
        admins = (await db.execute(select(AdminUser))).scalars().all()
        for a in admins:
            print(f"#{a.id} {a.email or '(telegram)'} tg={a.telegram_id} role={a.role.name} active={a.is_active}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VPN Robot management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-admin")
    p_create.add_argument("--email", required=True)
    p_create.add_argument("--password", required=True)
    p_create.add_argument("--role", default="super_admin")
    p_create.add_argument("--name", default="Admin")

    p_pwd = sub.add_parser("set-password")
    p_pwd.add_argument("--email", required=True)
    p_pwd.add_argument("--password", required=True)

    sub.add_parser("list-admins")

    args = parser.parse_args()
    if args.command == "create-admin":
        asyncio.run(_create_admin(args.email, args.password, args.role, args.name))
    elif args.command == "set-password":
        asyncio.run(_set_password(args.email, args.password))
    elif args.command == "list-admins":
        asyncio.run(_list_admins())


if __name__ == "__main__":
    main()
