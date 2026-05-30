"""Public payment-gateway callback (no auth — called by the gateway/redirect)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.v1.deps import DbSession
from app.core.exceptions import PaymentError
from app.core.logging import get_logger
from app.services import payment_service

logger = get_logger("payment.callback")
router = APIRouter(prefix="/payments", tags=["payments"])


def _extract_authority(params: dict) -> str | None:
    # ZarinPal: Authority ; IDPay: id ; NextPay: trans_id
    for key in ("Authority", "authority", "id", "trans_id"):
        if params.get(key):
            return params[key]
    return None


def _page(success: bool) -> str:
    title = "پرداخت موفق" if success else "پرداخت ناموفق"
    icon = "✅" if success else "❌"
    msg = (
        "پرداخت شما با موفقیت ثبت شد. به ربات بازگردید."
        if success
        else "پرداخت ناموفق بود یا لغو شد. در صورت کسر وجه، طی ۷۲ ساعت بازگردانده می‌شود."
    )
    color = "#16a34a" if success else "#dc2626"
    return f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>body{{font-family:Tahoma,sans-serif;background:#0f172a;color:#e2e8f0;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.card{{background:#1e293b;padding:2.5rem;border-radius:1rem;text-align:center;max-width:420px}}
.icon{{font-size:3rem}}.title{{color:{color};font-size:1.4rem;margin:1rem 0}}</style></head>
<body><div class="card"><div class="icon">{icon}</div>
<div class="title">{title}</div><p>{msg}</p></div></body></html>"""


@router.api_route("/callback", methods=["GET", "POST"])
async def payment_callback(request: Request, db: DbSession) -> HTMLResponse:
    params = dict(request.query_params)
    if request.method == "POST":
        try:
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})
        except Exception:  # noqa: BLE001 — best-effort form parsing
            pass

    authority = _extract_authority(params)
    status = (params.get("Status") or params.get("status") or "").upper()
    if status in {"NOK", "CANCELED", "FAILED"} or authority is None:
        return HTMLResponse(_page(False))

    try:
        _, ok = await payment_service.verify_and_settle(db, authority)
        await db.commit()
    except PaymentError as exc:
        logger.warning("callback_verify_error", error=str(exc))
        ok = False
    return HTMLResponse(_page(bool(ok)))
