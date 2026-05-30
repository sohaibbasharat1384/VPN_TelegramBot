"""Domain exceptions shared by services, API, and bots.

Services raise these framework-agnostic errors; the API layer maps them to HTTP
responses and the bots map them to Persian user-facing messages.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected business-rule violations."""

    code: str = "domain_error"
    # Persian message safe to show end users.
    user_message: str = "خطایی رخ داد. لطفاً دوباره تلاش کنید."

    def __init__(self, message: str | None = None, *, user_message: str | None = None):
        super().__init__(message or self.code)
        if user_message:
            self.user_message = user_message


class NotFoundError(DomainError):
    code = "not_found"
    user_message = "موردی یافت نشد."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    user_message = "شما مجاز به انجام این عمل نیستید."


class ValidationError(DomainError):
    code = "validation_error"
    user_message = "اطلاعات وارد شده نامعتبر است."


class InsufficientBalanceError(DomainError):
    code = "insufficient_balance"
    user_message = "موجودی کیف پول کافی نیست."


class OutOfStockError(DomainError):
    code = "out_of_stock"
    user_message = "متأسفانه موجودی این پلن به پایان رسیده است."


class CouponError(DomainError):
    code = "coupon_invalid"
    user_message = "کد تخفیف نامعتبر یا منقضی شده است."


class UserBannedError(DomainError):
    code = "user_banned"
    user_message = "دسترسی شما به ربات مسدود شده است."


class PaymentError(DomainError):
    code = "payment_error"
    user_message = "پرداخت با خطا مواجه شد."


class PanelIntegrationError(DomainError):
    code = "panel_error"
    user_message = "خطا در ارتباط با سرور. لطفاً با پشتیبانی تماس بگیرید."


class ConflictError(DomainError):
    code = "conflict"
    user_message = "این عمل به دلیل تداخل قابل انجام نیست."
