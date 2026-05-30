# Security Architecture

## Authentication (dashboard)
- **JWT access tokens** (HS256, 30 min) carry `sub`, `role`, `perms`, `jti`.
- **Rotating refresh tokens** (opaque, 14 days): only the SHA-256 hash is stored;
  on refresh the old token is revoked and linked to its replacement (reuse is
  detectable). Logout revokes the refresh token server-side.
- Passwords hashed with **bcrypt** (72-byte safe truncation). Login returns a
  uniform error — it never reveals whether the email or the password was wrong.

## Authorization (RBAC)
- Four seeded roles — `super_admin`, `admin`, `support`, `accountant` — mapped to
  fine-grained permission codes (`payments.approve`, `users.ban`, …).
- The API enforces permissions via the `require_permission(...)` dependency, which
  reads the admin's **live** permissions from the DB (not just the token claims).
- The admin Telegram bot enforces the same permission set per handler; the
  dashboard hides/locks UI the admin lacks permission for.

## Telegram bot trust
- The admin bot authenticates by Telegram `id` against `admin_users`; non-admins
  are rejected by middleware before any handler runs.
- Webhook mode (optional) verifies Telegram's `X-Telegram-Bot-Api-Secret-Token`.

## Audit logging
Every mutating admin/system action is recorded in `audit_logs` (actor, action,
target, IP, old/new value, timestamp). Nothing privileged happens without a log.

## Input / transport protection
- **SQL injection**: all DB access is via SQLAlchemy parameterized queries.
- **XSS**: the dashboard is React (auto-escaping); bot output uses controlled HTML.
- **CSRF**: the API is stateless Bearer-token auth (no cookies), so CSRF does not
  apply; tokens live in `localStorage` and are sent via the `Authorization` header.
- **CORS** is restricted to configured origins.
- **HTTPS/HSTS** enforced at Nginx; security headers set (`X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`).
- **Rate limiting**: Nginx `limit_req` on `/api` + app-level `RATE_LIMIT_PER_MINUTE`.

## Secrets & data at rest
- All secrets come from the environment; nothing is hardcoded. `.env` is git-ignored
  and `chmod 600`.
- **Panel credentials are encrypted at rest** (Fernet, key derived from
  `SECRET_KEY`) — never stored or returned in plaintext.
- Postgres/Redis are bound to the internal Docker network, not the public host.

## File uploads
Receipts/broadcast media are validated against `ALLOWED_UPLOAD_EXTENSIONS` and
`MAX_UPLOAD_SIZE_MB`; Telegram receipts are stored as `file_id` (no arbitrary
server-side paths from users).

## Money integrity
Amounts are integer Toman (no floats). Wallet debits/credits run inside a
transaction with `SELECT … FOR UPDATE` row locks and a `balance >= 0` DB CHECK,
so concurrent purchases/top-ups cannot corrupt balances or oversell inventory
(`FOR UPDATE SKIP LOCKED` reservation).

## Incident response
- Rotate `CUSTOMER_BOT_TOKEN`/`ADMIN_BOT_TOKEN` via BotFather if leaked.
- Rotate `SECRET_KEY`/`JWT_REFRESH_SECRET_KEY` (invalidates all sessions; note this
  also rotates the panel-credential encryption key — re-enter panel passwords).
- Review `audit_logs` and `payments` for anomalies; ban offending users.
