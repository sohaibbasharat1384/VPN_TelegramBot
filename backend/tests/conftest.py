"""Pytest fixtures: schema bootstrap + per-test async session (against CI Postgres)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import *  # noqa: F401,F403 — register all tables on the metadata


@pytest.fixture
async def _schema():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def db(_schema):
    """DB-backed session; requesting it provisions the schema (CI Postgres)."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
