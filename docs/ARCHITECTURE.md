# Architecture

## 1. Design principles

1. **Single source of truth for business logic.** Every meaningful operation
   (charge wallet, approve payment, create subscription, redeem coupon, grant
   referral reward) is implemented once in `backend/app/services/` and reused by
   the REST API, both Telegram bots, and Celery workers. Handlers and routes are
   thin adapters.
2. **Async everywhere.** FastAPI + SQLAlchemy 2.0 async engine + aiogram 3 +
   httpx for outbound calls. Celery handles work that must survive process
   restarts or run on a schedule.
3. **Explicit money.** All monetary amounts are stored as integer **Toman**
   (`BigInteger`), never floats. Currency math lives in `services/wallet.py`.
4. **Everything is auditable.** Mutating admin actions pass through
   `services/audit.py`, which records actor, action, target, old/new value, IP,
   and timestamp.
5. **Two fulfilment modes, side by side.** A plan is fulfilled either from
   **manual inventory** (`configs` table) or via **panel integration** (Marzban /
   X-UI). The `fulfilment_service` picks the strategy per plan.

## 2. Process topology

| Process        | Entry point                         | Responsibility |
|----------------|-------------------------------------|----------------|
| `api`          | `app.main:app` (uvicorn)            | REST API for the dashboard, payment callbacks, health |
| `customer_bot` | `app.bot.customer.main`             | Customer-facing Telegram bot |
| `admin_bot`    | `app.bot.admin.main`                | Admin Telegram panel |
| `worker`       | `celery -A app.workers.celery_app`  | Async jobs: notifications, panel sync, payment polling |
| `beat`         | `celery beat`                       | Scheduled jobs: expiry/usage alerts, inventory checks |
| `frontend`     | Next.js server                      | Web dashboard |

All Python processes share `backend/app/` and the same settings, models, and
services. Only the entry point differs.

## 3. Layered module map (`backend/app/`)

```
core/         Settings, security primitives, logging, exceptions, dependencies
db/           Engine, session factory, Base, seeding
models/       SQLAlchemy ORM models (one module per aggregate)
schemas/      Pydantic v2 request/response models
services/     Business logic (the real product) — framework-agnostic
api/v1/       FastAPI routers (thin) + auth/RBAC dependencies
integrations/ panels/ (Marzban, X-UI)  +  payments/ (ZarinPal, IDPay, NextPay)
workers/      Celery app + tasks + beat schedule
bot/          customer/ and admin/ aiogram apps (handlers + keyboards + FSM)
utils/        QR codes, formatting, Persian/RTL helpers, pagination
```

Dependency direction is strictly downward: `api`/`bot`/`workers` → `services` →
`models`/`integrations` → `core`/`db`. Services never import routers or handlers.

## 4. Request lifecycles

### Purchase (customer bot, manual-inventory plan)
1. User taps «خرید اشتراک جدید» → selects plan.
2. `order_service.create_pending_order()` reserves an inventory config (row lock,
   `SELECT … FOR UPDATE SKIP LOCKED`) so two buyers can't grab the same config.
3. Payment via wallet (instant) or card-to-card (admin approval) / gateway.
4. On payment confirmation → `fulfilment_service.deliver()` marks the config
   sold, attaches it to a `subscription`, and the bot sends link + QR + raw config.
5. `referral_service` and `audit_service` fire as side effects.

### Purchase (panel-integration plan)
Same flow, but `fulfilment_service` calls the configured panel adapter to create
the user and returns the generated subscription URL instead of consuming inventory.

### Card-to-card top-up
Upload receipt → `payment_service.create_manual_topup()` (status `pending`) →
admin bot notification → admin Approve/Reject → wallet credited + audit entry.

## 5. Security architecture

See [`SECURITY.md`](SECURITY.md). Summary: JWT access + rotating refresh tokens
for the dashboard, RBAC with 4 seeded roles + fine-grained permissions, audit log
on every mutation, rate limiting via Redis, signed Telegram webhooks, strict file
upload validation, and secrets only from environment.

## 6. Scheduled jobs (Celery beat)

| Job                          | Cadence   | Purpose |
|------------------------------|-----------|---------|
| `check_expiring_subscriptions` | hourly  | 7/3/1-day & expired alerts |
| `check_traffic_usage`          | 15 min  | 80/90/100% usage alerts (panel mode) |
| `sync_panel_users`             | 30 min  | Reconcile usage/expiry from panels |
| `check_low_inventory`          | hourly  | Notify admins when stock < threshold |
| `poll_pending_gateway_payments`| 5 min   | Reconcile unconfirmed gateway payments |
| `expire_stale_orders`          | 15 min  | Release inventory reserved by abandoned orders |
