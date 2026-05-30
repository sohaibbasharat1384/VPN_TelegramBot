"""Persian (RTL) strings for the admin bot."""
from __future__ import annotations

PANEL_TITLE = "🛠 پنل مدیریت"
NOT_ADMIN = "⛔️ شما دسترسی مدیریت ندارید."
NO_PERMISSION = "⛔️ شما مجوز این بخش را ندارید."
MENU = "بخش موردنظر را انتخاب کنید:"
CANCELLED = "عملیات لغو شد."
DONE = "✅ انجام شد."

# Menu buttons
BTN_PAYMENTS = "💳 پرداخت‌های در انتظار"
BTN_STATS = "📊 آمار"
BTN_USERS = "👥 کاربران"
BTN_TICKETS = "🎫 تیکت‌ها"
BTN_INVENTORY = "📦 انبار"
BTN_COUPONS = "🏷 کدهای تخفیف"
BTN_CARDS = "💳 مدیریت کارت‌ها"
BTN_BROADCAST = "📣 پیام همگانی"
BTN_BACK = "🔙 بازگشت"
BTN_CANCEL = "❌ انصراف"

# Payments
NO_PENDING_PAYMENTS = "پرداخت در انتظاری وجود ندارد."
PAYMENT_CARD = (
    "💳 <b>پرداخت #{id}</b>\n"
    "کاربر: {user}\n"
    "نوع: {purpose}\n"
    "مبلغ: <b>{amount}</b>\n"
    "شمارهٔ پیگیری: {tracking}"
)
BTN_APPROVE = "✅ تأیید"
BTN_REJECT = "❌ رد"
PAYMENT_APPROVED = "✅ پرداخت #{id} تأیید شد."
PAYMENT_REJECTED = "❌ پرداخت #{id} رد شد."

# Users
ENTER_USER_QUERY = "🔎 شناسهٔ عددی، نام کاربری یا کد معرف را وارد کنید:"
NO_USER_FOUND = "کاربری یافت نشد."
USER_PROFILE = (
    "👤 <b>{name}</b>\n"
    "شناسه: <code>{tid}</code>\n"
    "موجودی کیف پول: <b>{balance}</b>\n"
    "کد معرف: <code>{ref}</code>\n"
    "وضعیت: {status}\n"
    "تاریخ عضویت: {joined}"
)
BTN_BAN = "🚫 مسدودسازی"
BTN_UNBAN = "✅ رفع مسدودی"
BTN_ADJUST = "💰 تنظیم موجودی"
ENTER_ADJUST = "مبلغ تغییر موجودی را وارد کنید (مثبت یا منفی، به تومان):"
ADJUST_DONE = "✅ موجودی به‌روزرسانی شد. موجودی جدید: {balance}"

# Tickets
NO_OPEN_TICKETS = "تیکت بازی وجود ندارد."
TICKET_VIEW = "🎫 <b>تیکت #{id}</b> — {subject}\nوضعیت: {status}\n\n{body}"
BTN_REPLY = "✍️ پاسخ"
BTN_CLOSE = "🔒 بستن"
ENTER_REPLY = "پاسخ خود را برای تیکت #{id} بنویسید:"
REPLY_SENT = "✅ پاسخ ارسال شد."

# Inventory
INVENTORY_HEADER = "📦 وضعیت انبار:"
INVENTORY_ROW = "• {title}: آماده {available} | فروخته {sold}"
BTN_ADD_CONFIG = "➕ افزودن کانفیگ"
CHOOSE_PLAN_FOR_CONFIG = "برای کدام پلن کانفیگ اضافه می‌کنید؟"
ENTER_CONFIG_URL = "لینک اشتراک (subscription URL) را ارسال کنید:"
ENTER_CONFIG_RAW = "کانفیگ خام (raw config) را ارسال کنید:"
CONFIG_ADDED = "✅ کانفیگ به انبار پلن «{title}» اضافه شد."

# Coupons
NO_COUPONS = "کد تخفیفی ثبت نشده است."
COUPON_ROW = "🏷 {code} — {value} ({uses} استفاده) — {status}"
BTN_NEW_COUPON = "➕ کد جدید"
ENTER_COUPON_CODE = "کد تخفیف را وارد کنید:"
ENTER_COUPON_TYPE = "نوع تخفیف: «درصدی» یا «مبلغی»؟"
ENTER_COUPON_VALUE = "مقدار تخفیف را وارد کنید (درصد یا مبلغ به تومان):"
COUPON_CREATED = "✅ کد تخفیف «{code}» ساخته شد."

# Cards
NO_CARDS = "کارتی ثبت نشده است."
CARD_ROW = "💳 {bank} — {number} ({holder}) — {status}"
BTN_NEW_CARD = "➕ کارت جدید"
ENTER_CARD_NUMBER = "شمارهٔ کارت را وارد کنید:"
ENTER_CARD_HOLDER = "نام صاحب کارت را وارد کنید:"
ENTER_CARD_BANK = "نام بانک را وارد کنید:"
CARD_ADDED = "✅ کارت اضافه شد."

# Broadcast
BROADCAST_TARGET = "مخاطب پیام را انتخاب کنید:"
BTN_TARGET_ALL = "👥 همهٔ کاربران"
BTN_TARGET_ACTIVE = "✅ کاربران فعال"
ENTER_BROADCAST = "متن یا رسانهٔ پیام همگانی را ارسال کنید:"
BROADCAST_QUEUED = "✅ پیام همگانی در صف ارسال قرار گرفت."

# Stats
STATS_TEXT = (
    "📊 <b>آمار کلی</b>\n\n"
    "👥 کل کاربران: {total_users}\n"
    "✅ کاربران فعال: {active_users}\n"
    "🆕 کاربران امروز: {daily_users}\n"
    "📦 اشتراک‌های فعال: {active_subs}\n\n"
    "💰 درآمد امروز: {rev_day}\n"
    "💰 درآمد هفته: {rev_week}\n"
    "💰 درآمد ماه: {rev_month}\n\n"
    "👛 مجموع کیف پول‌ها: {wallet_total}\n"
    "🎁 مجموع پاداش معرفی: {referral_total}"
)
