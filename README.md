# VPN Robot — Telegram V2Ray Sales Platform

پلتفرم فروش اشتراک V2Ray از طریق تلگرام و داشبورد وب (فارسی، RTL).

An enterprise-grade, production-oriented platform for selling V2Ray subscriptions
through Telegram, with a full web admin dashboard.

## Components

| Component        | Stack                                   | Path        |
|------------------|-----------------------------------------|-------------|
| Backend API      | Python 3.12, FastAPI, SQLAlchemy 2 (async) | `backend/`  |
| Customer Bot     | Aiogram 3.x                             | `backend/app/bot/customer/` |
| Admin Bot        | Aiogram 3.x                             | `backend/app/bot/admin/` |
| Background Jobs  | Celery + Redis                          | `backend/app/workers/` |
| Web Dashboard    | Next.js, TypeScript, Tailwind, Shadcn/UI | `frontend/` |
| Database         | PostgreSQL 16                           | —           |
| Cache / Broker   | Redis 7                                 | —           |

## Architecture at a glance

```
                     ┌──────────────────────────┐
   Telegram users ──▶│  Customer Bot (aiogram)  │──┐
                     └──────────────────────────┘  │
                     ┌──────────────────────────┐  │   ┌──────────────┐
   Admins        ──▶│   Admin Bot (aiogram)     │──┼──▶│  FastAPI API │──▶ PostgreSQL
                     └──────────────────────────┘  │   │  (services)  │──▶ Redis
                     ┌──────────────────────────┐  │   └──────┬───────┘
   Staff (web)   ──▶│  Next.js Dashboard        │──┘          │
                     └──────────────────────────┘             ▼
                                                        ┌────────────┐
                                                        │   Celery   │──▶ Panel APIs
                                                        │  workers   │    (Marzban / X-UI)
                                                        └────────────┘    Payment gateways
```

All business logic lives in `backend/app/services/` so the bots, the REST API,
and the workers share one source of truth.

## Quick start (development)

```bash
cp .env.example .env          # then edit secrets
docker compose up -d --build  # postgres, redis, api, worker, beat, bots, frontend
docker compose exec api alembic upgrade head
```

API docs: `http://localhost:8000/docs` · Dashboard: `http://localhost:3000`

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design & module map
- [`docs/DATABASE.md`](docs/DATABASE.md) — ERD, tables, constraints, indexes
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Ubuntu production deployment guide
- [`docs/SECURITY.md`](docs/SECURITY.md) — security architecture

## Configuration modes

The platform supports **manual inventory** and **panel integration** (Marzban /
Sanaei X-UI) simultaneously, toggleable per-plan from the admin panel without code
changes.

## License

Proprietary — commercial use.
