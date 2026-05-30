"""Security primitives: password hashing, JWT, token & secret handling.

Higher-level auth flows (login, refresh rotation, RBAC dependencies) live in
``app/services/auth.py`` and ``app/api/v1/deps.py`` and build on these.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

# bcrypt operates on at most 72 bytes; longer inputs are truncated consistently.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


# --------------------------------------------------------------------------- #
# Passwords (bcrypt directly — passlib is unmaintained)
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# JWT access tokens
# --------------------------------------------------------------------------- #
def create_access_token(
    subject: str | int,
    *,
    role: str,
    permissions: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "perms": permissions,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


# --------------------------------------------------------------------------- #
# Refresh tokens — opaque random strings; only their hash is stored.
# --------------------------------------------------------------------------- #
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)


# --------------------------------------------------------------------------- #
# Symmetric encryption for stored panel credentials.
# Key is derived deterministically from SECRET_KEY so it survives restarts.
# --------------------------------------------------------------------------- #
def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


# --------------------------------------------------------------------------- #
# Telegram webhook signature verification.
# --------------------------------------------------------------------------- #
def verify_telegram_webhook(secret_header: str | None) -> bool:
    if not settings.telegram_webhook_secret:
        return True
    if not secret_header:
        return False
    return hmac.compare_digest(secret_header, settings.telegram_webhook_secret)
