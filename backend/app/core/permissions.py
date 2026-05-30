"""Canonical permission codes and the seeded role→permission mapping.

A single source of truth consumed by the seed migration, the RBAC dependencies,
and the dashboard (which fetches the current admin's permission list).
"""
from __future__ import annotations


class Perm:
    # Dashboard / overview
    DASHBOARD_VIEW = "dashboard.view"
    STATS_VIEW = "stats.view"

    # Users
    USERS_VIEW = "users.view"
    USERS_EDIT = "users.edit"
    USERS_BAN = "users.ban"
    WALLET_ADJUST = "wallet.adjust"

    # Payments / finance
    PAYMENTS_VIEW = "payments.view"
    PAYMENTS_APPROVE = "payments.approve"
    PAYMENTS_EXPORT = "payments.export"

    # Catalog & inventory
    PLANS_MANAGE = "plans.manage"
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_MANAGE = "inventory.manage"

    # Coupons & referrals
    COUPONS_MANAGE = "coupons.manage"
    REFERRALS_MANAGE = "referrals.manage"

    # Tickets
    TICKETS_VIEW = "tickets.view"
    TICKETS_REPLY = "tickets.reply"

    # Broadcast & cards
    BROADCAST_SEND = "broadcast.send"
    CARDS_MANAGE = "cards.manage"

    # Panels & settings
    PANELS_MANAGE = "panels.manage"
    SETTINGS_MANAGE = "settings.manage"

    # Admin & audit
    ADMINS_MANAGE = "admins.manage"
    AUDIT_VIEW = "audit.view"


PERMISSION_DESCRIPTIONS: dict[str, str] = {
    Perm.DASHBOARD_VIEW: "مشاهده داشبورد",
    Perm.STATS_VIEW: "مشاهده آمار",
    Perm.USERS_VIEW: "مشاهده کاربران",
    Perm.USERS_EDIT: "ویرایش کاربران",
    Perm.USERS_BAN: "مسدودسازی کاربران",
    Perm.WALLET_ADJUST: "تنظیم موجودی کیف پول",
    Perm.PAYMENTS_VIEW: "مشاهده تراکنش‌ها",
    Perm.PAYMENTS_APPROVE: "تأیید/رد پرداخت",
    Perm.PAYMENTS_EXPORT: "خروجی مالی",
    Perm.PLANS_MANAGE: "مدیریت پلن‌ها و قیمت‌ها",
    Perm.INVENTORY_VIEW: "مشاهده انبار",
    Perm.INVENTORY_MANAGE: "مدیریت انبار",
    Perm.COUPONS_MANAGE: "مدیریت کدهای تخفیف",
    Perm.REFERRALS_MANAGE: "مدیریت زیرمجموعه‌گیری",
    Perm.TICKETS_VIEW: "مشاهده تیکت‌ها",
    Perm.TICKETS_REPLY: "پاسخ به تیکت‌ها",
    Perm.BROADCAST_SEND: "ارسال پیام همگانی",
    Perm.CARDS_MANAGE: "مدیریت کارت‌ها",
    Perm.PANELS_MANAGE: "مدیریت پنل‌ها",
    Perm.SETTINGS_MANAGE: "مدیریت تنظیمات",
    Perm.ADMINS_MANAGE: "مدیریت مدیران",
    Perm.AUDIT_VIEW: "مشاهده لاگ فعالیت‌ها",
}

ALL_PERMISSIONS: list[str] = list(PERMISSION_DESCRIPTIONS.keys())

# Seeded roles
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_SUPPORT = "support"
ROLE_ACCOUNTANT = "accountant"

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_SUPER_ADMIN: "دسترسی کامل",
    ROLE_ADMIN: "مدیریت محدود",
    ROLE_SUPPORT: "فقط پشتیبانی و تیکت",
    ROLE_ACCOUNTANT: "فقط دسترسی مالی",
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    ROLE_SUPER_ADMIN: ALL_PERMISSIONS,
    ROLE_ADMIN: [
        Perm.DASHBOARD_VIEW, Perm.STATS_VIEW,
        Perm.USERS_VIEW, Perm.USERS_EDIT, Perm.USERS_BAN, Perm.WALLET_ADJUST,
        Perm.PAYMENTS_VIEW, Perm.PAYMENTS_APPROVE,
        Perm.PLANS_MANAGE, Perm.INVENTORY_VIEW, Perm.INVENTORY_MANAGE,
        Perm.COUPONS_MANAGE, Perm.REFERRALS_MANAGE,
        Perm.TICKETS_VIEW, Perm.TICKETS_REPLY,
        Perm.BROADCAST_SEND, Perm.CARDS_MANAGE,
    ],
    ROLE_SUPPORT: [
        Perm.DASHBOARD_VIEW,
        Perm.USERS_VIEW,
        Perm.TICKETS_VIEW, Perm.TICKETS_REPLY,
    ],
    ROLE_ACCOUNTANT: [
        Perm.DASHBOARD_VIEW, Perm.STATS_VIEW,
        Perm.PAYMENTS_VIEW, Perm.PAYMENTS_APPROVE, Perm.PAYMENTS_EXPORT,
        Perm.USERS_VIEW,
    ],
}

DEFAULT_SETTINGS: dict[str, object] = {
    "referral_reward_amount": 10000,   # Toman credited to referrer
    "referral_threshold": 1,           # qualifying purchases before reward
    "low_inventory_threshold": 5,
    "card_to_card_enabled": True,
    "gateway_enabled": False,
}
