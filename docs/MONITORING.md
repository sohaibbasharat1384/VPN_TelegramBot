# Monitoring

## Health & liveness
- `GET /health` — cheap liveness for uptime monitors (UptimeRobot, BetterStack).
- Every container defines a Docker `healthcheck`; `docker compose ps` shows health.

## Logs
All processes emit **structured JSON logs** (structlog) to stdout in production.
- Local: `docker compose logs -f --tail=200 api worker beat customer_bot admin_bot`
- Aggregate: point the Docker logging driver at Loki/Promtail, Vector, or a hosted
  service. Each line has `event`, `level`, `timestamp`, and contextual fields.

Key events to alert on: `telegram_send_failed`, `panel_*_failed`, `*_request_failed`
(gateway), and any `level=error`.

## Metrics & resources
- `docker stats` for live CPU/memory per container.
- Celery: inspect the worker with
  `docker compose exec worker celery -A app.workers.celery_app inspect active`
  and `... inspect stats`.
- DB: `docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "select state, count(*) from pg_stat_activity group by 1;"`

## Suggested alerts
| Signal | Threshold | Action |
|--------|-----------|--------|
| `/health` down | 2 consecutive failures | page on-call |
| api 5xx rate | > 2% over 5 min | investigate logs |
| Celery queue backlog | broker list length grows | scale `worker` concurrency |
| Pending payments | > N for > 1h | remind admins (bot already alerts) |
| Disk usage | > 80% | prune images, check backups dir |
| Low inventory | per-plan threshold | handled in-app (admin bot alert) |

## Business monitoring
The dashboard **Overview** and the admin bot **«📊 آمار»** expose users, active
subscriptions, daily/weekly/monthly revenue, wallet totals, and referral payouts —
no extra tooling required for day-to-day operations.
