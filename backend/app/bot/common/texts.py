"""Persian (RTL) button labels and message templates for the customer bot."""
from __future__ import annotations

# ---- Main menu buttons ----
BTN_BUY = "🛒 خرید اشتراک جدید"
BTN_RENEW = "♻️ تمدید اشتراک"
BTN_WALLET = "👛 کیف پول"
BTN_REFERRAL = "🎁 معرفی به دوستان"
BTN_TICKETS = "🎫 تیکت پشتیبانی"
BTN_COUPON = "🏷 کد تخفیف"
BTN_MY_SUBS = "📦 اشتراک‌های من"

# ---- Common ----
BTN_BACK = "🔙 بازگشت"
BTN_CANCEL = "❌ انصراف"
BTN_MAIN_MENU = "🏠 منوی اصلی"

WELCOME = (
    "👋 سلام {name} عزیز!\n\n"
    "به ربات فروش اشتراک خوش آمدید.\n"
    "از منوی زیر گزینهٔ موردنظر را انتخاب کنید."
)
MAIN_MENU = "یکی از گزینه‌های زیر را انتخاب کنید:"
BANNED = "⛔️ دسترسی شما به ربات مسدود شده است."
CANCELLED = "عملیات لغو شد."
UNKNOWN = "متوجه نشدم. لطفاً از دکمه‌های منو استفاده کنید."

# ---- Buy ----
CHOOSE_PLAN = "📋 لطفاً پلن موردنظر را انتخاب کنید:"
PLAN_DETAIL = (
    "📦 <b>{title}</b>\n"
    "حجم: {volume}\n"
    "مدت: {days} روز\n"
    "قیمت: <b>{price}</b>\n\n"
    "روش پرداخت را انتخاب کنید:"
)
NO_PLANS = "در حال حاضر پلنی برای فروش موجود نیست."
PAY_WALLET = "👛 پرداخت از کیف پول"
PAY_CARD = "💳 کارت به کارت"
PAY_GATEWAY = "🌐 درگاه پرداخت آنلاین"
APPLY_COUPON = "🏷 اعمال کد تخفیف"
OUT_OF_STOCK = "متأسفانه موجودی این پلن به پایان رسیده است."
DELIVERED = (
    "✅ خرید شما با موفقیت انجام شد!\n\n"
    "🔗 لینک اشتراک:\n<code>{url}</code>\n\n"
    "تاریخ انقضا: {expires}\n"
    "حجم: {volume}\n\n"
    "تصویر QR و کانفیگ در پیام‌های بعدی ارسال می‌شود."
)
RAW_CONFIG_CAPTION = "📄 کانفیگ شما (برای کپی لمس کنید):"
QR_CAPTION = "📱 برای افزودن سریع، QR را اسکن کنید."

# ---- Wallet ----
WALLET_INFO = "👛 موجودی کیف پول شما: <b>{balance}</b>"
BTN_CHARGE = "➕ شارژ کیف پول"
BTN_WALLET_HISTORY = "🧾 تاریخچهٔ تراکنش‌ها"
ENTER_CHARGE_AMOUNT = "💰 مبلغ موردنظر برای شارژ را به تومان وارد کنید:"
INVALID_AMOUNT = "مبلغ نامعتبر است. یک عدد صحیح به تومان وارد کنید."
CHOOSE_CHARGE_METHOD = "روش شارژ را انتخاب کنید:"
CARD_INFO = (
    "💳 لطفاً مبلغ <b>{amount}</b> را به کارت زیر واریز کنید:\n\n"
    "شمارهٔ کارت: <code>{card_number}</code>\n"
    "به نام: {card_holder}\n"
    "بانک: {bank_name}\n\n"
    "سپس شمارهٔ پیگیری را ارسال و تصویر رسید را آپلود کنید."
)
NO_CARD = "در حال حاضر کارتی برای واریز ثبت نشده است. لطفاً با پشتیبانی تماس بگیرید."
ENTER_TRACKING = "🔢 لطفاً شمارهٔ پیگیری تراکنش را وارد کنید:"
SEND_RECEIPT = "🧾 لطفاً تصویر رسید را ارسال کنید:"
TOPUP_SUBMITTED = "✅ درخواست شارژ شما ثبت شد و پس از تأیید مدیر، اعمال می‌شود."
GATEWAY_REDIRECT = "برای پرداخت روی دکمهٔ زیر بزنید:"
BTN_PAY_NOW = "🌐 پرداخت"
WALLET_EMPTY_HISTORY = "تراکنشی ثبت نشده است."

# ---- Referral ----
REFERRAL_INFO = (
    "🎁 <b>دعوت از دوستان</b>\n\n"
    "با دعوت دوستان خود، پس از اولین خرید آن‌ها پاداش دریافت کنید!\n\n"
    "🔗 لینک اختصاصی شما:\n{link}\n\n"
    "👥 تعداد دعوت‌ها: <b>{total}</b>\n"
    "💰 مجموع پاداش دریافتی: <b>{earned}</b>"
)

# ---- Tickets ----
TICKETS_MENU = "🎫 بخش پشتیبانی"
BTN_NEW_TICKET = "📝 تیکت جدید"
BTN_MY_TICKETS = "📂 تیکت‌های من"
ENTER_TICKET_SUBJECT = "موضوع تیکت را وارد کنید:"
ENTER_TICKET_BODY = "متن پیام خود را بنویسید (می‌توانید تصویر هم ارسال کنید):"
TICKET_CREATED = "✅ تیکت شما با شمارهٔ #{id} ثبت شد. به‌زودی پاسخ داده می‌شود."
NO_TICKETS = "تیکتی ندارید."
TICKET_ROW = "#{id} — {subject} ({status})"
TICKET_REPLY_PROMPT = "پاسخ خود را برای تیکت #{id} بنویسید:"
TICKET_REPLY_SENT = "✅ پاسخ شما ثبت شد."
TICKET_CLOSED_MSG = "تیکت بسته شد."

# ---- Renew / subscriptions ----
NO_ACTIVE_SUBS = "اشتراک فعالی ندارید."
SUB_ROW = "📦 {title}\nانقضا: {expires}\nمصرف: {used} از {limit}\nوضعیت: {status}"
BTN_RENEW_THIS = "♻️ تمدید"

# ---- Coupon ----
ENTER_COUPON = "🏷 کد تخفیف را وارد کنید:"
COUPON_APPLIED = "✅ کد تخفیف اعمال شد. تخفیف: {discount}"
COUPON_CLEARED = "کد تخفیف حذف شد."

STATUS_FA = {
    "active": "فعال",
    "expired": "منقضی",
    "disabled": "غیرفعال",
    "open": "باز",
    "pending": "در انتظار",
    "answered": "پاسخ داده شده",
    "closed": "بسته",
}
