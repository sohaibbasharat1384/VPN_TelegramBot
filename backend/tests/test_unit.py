"""Pure-function unit tests (no DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core import security
from app.models.coupon import Coupon
from app.models.enums import DiscountType
from app.services.coupon_service import compute_discount
from app.utils.formatting import human_bytes, to_fa_digits, toman


def test_password_round_trip():
    h = security.hash_password("correct horse battery staple")
    assert security.verify_password("correct horse battery staple", h)
    assert not security.verify_password("wrong", h)


def test_jwt_round_trip():
    token = security.create_access_token(7, role="admin", permissions=["users.view"])
    payload = security.decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "admin"
    assert "users.view" in payload["perms"]


def test_fernet_round_trip():
    enc = security.encrypt_secret("panel-password")
    assert enc != "panel-password"
    assert security.decrypt_secret(enc) == "panel-password"


def _coupon(dtype: DiscountType, value: int) -> Coupon:
    return Coupon(
        code="X", discount_type=dtype, discount_value=value,
        used_count=0, per_user_limit=1, min_order_amount=0, is_active=True,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def test_compute_discount_percent_and_fixed_and_cap():
    assert compute_discount(_coupon(DiscountType.percent, 20), 100_000) == 20_000
    assert compute_discount(_coupon(DiscountType.fixed, 30_000), 100_000) == 30_000
    # discount never exceeds the order amount
    assert compute_discount(_coupon(DiscountType.fixed, 200_000), 100_000) == 100_000


def test_formatting_helpers():
    assert to_fa_digits("123") == "۱۲۳"
    assert "تومان" in toman(50_000)
    assert "GB" in human_bytes(5 * 1024**3)
