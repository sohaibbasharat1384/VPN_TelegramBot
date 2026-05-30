# Backup & Recovery

## What is backed up
- **PostgreSQL** — full `pg_dump` in custom format (`db-<stamp>.dump`).
- **Media volume** — uploaded receipts and broadcast assets (`media-<stamp>.tar.gz`).

Redis holds only cache + Celery broker + FSM state; it is **not** backed up
(everything in it is reconstructable). Make sure Redis AOF persistence is on
(it is, in `docker-compose.yml`) so in-flight jobs survive restarts.

## Schedule
`deploy/backup.sh` runs nightly at 03:30 via cron (see DEPLOYMENT §10), keeps
14 days locally, and optionally syncs to S3 (`BACKUP_S3_BUCKET` + AWS creds).

## Restore — database
```bash
cd /opt/vpnrobot
# Stop writers so the restore is consistent
docker compose stop api worker beat customer_bot admin_bot

# Recreate a clean database and restore
docker compose exec -T postgres dropdb   -U "$POSTGRES_USER" "$POSTGRES_DB"
docker compose exec -T postgres createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
cat /var/backups/vpnrobot/db-<stamp>.dump | \
  docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner

docker compose up -d
```

## Restore — media
```bash
docker run --rm -v vpnrobot_media:/media -v /var/backups/vpnrobot:/backup alpine \
  sh -c "cd /media && tar xzf /backup/media-<stamp>.tar.gz"
```

## Disaster recovery (new server)
1. Provision per DEPLOYMENT §1–5 (clone, `.env`, `docker compose up -d`).
2. Restore DB + media from the latest off-box backup (above).
3. `docker compose exec api alembic upgrade head` (no-op if already current).
4. Re-point DNS; bots reconnect automatically (long polling).

## Verify backups regularly
Restore the latest dump into a throwaway database monthly:
```bash
docker compose exec -T postgres createdb -U "$POSTGRES_USER" vpnrobot_verify
cat db-<stamp>.dump | docker compose exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d vpnrobot_verify --no-owner
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d vpnrobot_verify \
  -c "select count(*) from users;"
docker compose exec -T postgres dropdb -U "$POSTGRES_USER" vpnrobot_verify
```
