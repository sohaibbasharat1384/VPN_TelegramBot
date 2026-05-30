#!/usr/bin/env bash
# Nightly backup: PostgreSQL dump + media volume, with rotation + optional S3.
# Install via cron (see docs/DEPLOYMENT.md §10).
set -euo pipefail

APP_DIR="/opt/vpnrobot"
BACKUP_DIR="/var/backups/vpnrobot"
RETENTION_DAYS=14
STAMP="$(date +%Y%m%d-%H%M%S)"

cd "$APP_DIR"
# shellcheck disable=SC1091
set -a; source .env; set +a

mkdir -p "$BACKUP_DIR"

echo "[$(date)] starting backup $STAMP"

# 1) Database (custom format for fast, selective restore)
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" \
  > "$BACKUP_DIR/db-$STAMP.dump"

# 2) Media (uploaded receipts, broadcast assets)
docker run --rm -v vpnrobot_media:/media -v "$BACKUP_DIR":/backup alpine \
  tar czf "/backup/media-$STAMP.tar.gz" -C /media .

# 3) Rotate local copies
find "$BACKUP_DIR" -name 'db-*.dump'    -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete

# 4) Off-box copy (optional). Configure AWS creds + BACKUP_S3_BUCKET in env.
if [ -n "${BACKUP_S3_BUCKET:-}" ] && command -v aws >/dev/null; then
  aws s3 cp "$BACKUP_DIR/db-$STAMP.dump"      "s3://$BACKUP_S3_BUCKET/db/"
  aws s3 cp "$BACKUP_DIR/media-$STAMP.tar.gz" "s3://$BACKUP_S3_BUCKET/media/"
fi

echo "[$(date)] backup $STAMP complete"
