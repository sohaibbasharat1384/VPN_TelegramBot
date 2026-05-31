#!/usr/bin/env bash
# =============================================================================
#  VPN Robot — Quick Install for Ubuntu VPS
#
#  Installs Docker, generates secrets, writes .env, builds & starts the whole
#  stack, runs migrations, optionally configures Nginx + Let's Encrypt, and
#  creates the first web-dashboard admin.
#
#  Usage (interactive):
#     git clone https://github.com/sohaibbasharat1384/VPN_TelegramBot.git
#     cd VPN_TelegramBot
#     sudo bash deploy/install.sh
#
#  Usage (unattended) — set these env vars before running:
#     VR_CUSTOMER_BOT_TOKEN, VR_ADMIN_BOT_TOKEN, VR_SUPER_ADMINS,
#     VR_DOMAIN (optional), VR_LE_EMAIL (for SSL),
#     VR_ADMIN_EMAIL, VR_ADMIN_PASSWORD, VR_PAYMENT_PROVIDER (optional),
#     VR_NONINTERACTIVE=1
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/sohaibbasharat1384/VPN_TelegramBot.git"
INSTALL_DIR_DEFAULT="/opt/vpnrobot"

# ---- pretty output ----------------------------------------------------------
c_blue=$'\033[1;34m'; c_green=$'\033[1;32m'; c_yellow=$'\033[1;33m'
c_red=$'\033[1;31m'; c_reset=$'\033[0m'
log()  { echo "${c_blue}▶${c_reset} $*"; }
ok()   { echo "${c_green}✔${c_reset} $*"; }
warn() { echo "${c_yellow}⚠${c_reset} $*"; }
die()  { echo "${c_red}✘${c_reset} $*" >&2; exit 1; }

NONINTERACTIVE="${VR_NONINTERACTIVE:-0}"

ask() {  # ask VARNAME "Prompt" "default" ; honors VR_<UPPER> env override
  local __var="$1" prompt="$2" default="${3:-}"
  local envname="VR_${__var}"
  local envval="${!envname:-}"
  if [ -n "$envval" ]; then printf -v "$__var" '%s' "$envval"; return; fi
  if [ "$NONINTERACTIVE" = "1" ]; then printf -v "$__var" '%s' "$default"; return; fi
  local input
  if [ -n "$default" ]; then read -rp "$prompt [$default]: " input || true
  else read -rp "$prompt: " input || true; fi
  printf -v "$__var" '%s' "${input:-$default}"
}

ask_secret() {  # ask_secret VARNAME "Prompt"
  local __var="$1" prompt="$2"
  local envname="VR_${__var}"
  local envval="${!envname:-}"
  if [ -n "$envval" ]; then printf -v "$__var" '%s' "$envval"; return; fi
  if [ "$NONINTERACTIVE" = "1" ]; then printf -v "$__var" '%s' ""; return; fi
  local input; read -rsp "$prompt: " input || true; echo; printf -v "$__var" '%s' "$input"
}

set_env() {  # set_env KEY VALUE FILE  (update in place or append)
  local key="$1" val="$2" file="$3" esc
  esc=$(printf '%s' "$val" | sed -e 's/[\/&|]/\\&/g')
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${esc}|" "$file"
  else
    echo "${key}=${val}" >> "$file"
  fi
}

require_root() {
  [ "$(id -u)" -eq 0 ] || die "Please run as root or with sudo: sudo bash deploy/install.sh"
}

# ---- 0. preconditions -------------------------------------------------------
require_root
command -v apt-get >/dev/null || die "This installer targets Ubuntu/Debian (apt)."
log "Updating package lists..."
apt-get update -qq
apt-get install -y -qq git curl ca-certificates openssl ufw >/dev/null
ok "Base packages ready."

# ---- 1. locate or clone the project ----------------------------------------
if [ -f "docker-compose.yml" ] && [ -d "backend" ]; then
  APP_DIR="$(pwd)"
  log "Using project in current directory: $APP_DIR"
else
  ask APP_DIR "Install directory" "$INSTALL_DIR_DEFAULT"
  if [ ! -d "$APP_DIR/.git" ]; then
    log "Cloning $REPO_URL -> $APP_DIR"
    mkdir -p "$APP_DIR"
    git clone --depth 1 "$REPO_URL" "$APP_DIR"
  else
    log "Repo already present at $APP_DIR; pulling latest"
    git -C "$APP_DIR" pull --ff-only || warn "git pull skipped"
  fi
fi
cd "$APP_DIR"

# ---- 2. install Docker + compose plugin ------------------------------------
if ! command -v docker >/dev/null; then
  log "Installing Docker Engine..."
  curl -fsSL https://get.docker.com | sh >/dev/null
  systemctl enable --now docker >/dev/null 2>&1 || true
  ok "Docker installed."
else
  ok "Docker already installed ($(docker --version))."
fi
docker compose version >/dev/null 2>&1 || die "docker compose v2 plugin not available."

# ---- 3. gather configuration ------------------------------------------------
echo
log "Configuration (press Enter to accept defaults; required fields are marked *)"
ask        CUSTOMER_BOT_TOKEN "* Customer bot token (from @BotFather)" ""
ask        ADMIN_BOT_TOKEN    "* Admin bot token (from @BotFather)" ""
ask        SUPER_ADMINS       "* Your Telegram numeric ID(s), comma-separated" ""
ask        DOMAIN             "Domain for the dashboard/API (blank = IP, no SSL)" ""
ask        PAYMENT_PROVIDER   "Payment gateway (zarinpal|idpay|nextpay|none)" "none"

[ -n "$CUSTOMER_BOT_TOKEN" ] || warn "No customer bot token set — set it in .env later."
[ -n "$ADMIN_BOT_TOKEN" ]    || warn "No admin bot token set — set it in .env later."
[ -n "$SUPER_ADMINS" ]       || warn "No super-admin Telegram ID set — set BOOTSTRAP_SUPER_ADMINS later."

# ---- 4. write .env ----------------------------------------------------------
if [ -f .env ]; then
  ask OVERWRITE_ENV ".env already exists. Regenerate it? (y/N)" "N"
  [ "${OVERWRITE_ENV,,}" = "y" ] || { ok "Keeping existing .env."; SKIP_ENV=1; }
fi

if [ "${SKIP_ENV:-0}" != "1" ]; then
  log "Generating .env with strong random secrets..."
  cp -f .env.example .env
  SECRET_KEY="$(openssl rand -hex 32)"
  REFRESH_KEY="$(openssl rand -hex 32)"
  DB_PASS="$(openssl rand -hex 24)"
  WEBHOOK_SECRET="$(openssl rand -hex 16)"

  set_env SECRET_KEY "$SECRET_KEY" .env
  set_env JWT_REFRESH_SECRET_KEY "$REFRESH_KEY" .env
  set_env POSTGRES_PASSWORD "$DB_PASS" .env
  set_env DATABASE_URL "postgresql+asyncpg://vpnrobot:${DB_PASS}@postgres:5432/vpnrobot" .env
  set_env TELEGRAM_WEBHOOK_SECRET "$WEBHOOK_SECRET" .env
  set_env ENVIRONMENT "production" .env
  set_env DEBUG "false" .env

  set_env CUSTOMER_BOT_TOKEN "$CUSTOMER_BOT_TOKEN" .env
  set_env ADMIN_BOT_TOKEN "$ADMIN_BOT_TOKEN" .env
  set_env BOOTSTRAP_SUPER_ADMINS "$SUPER_ADMINS" .env

  if [ -n "$DOMAIN" ]; then
    BASE="https://${DOMAIN}"
  else
    IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo localhost)"
    BASE="http://${IP}:8000"
  fi
  set_env API_BASE_URL "$BASE" .env
  set_env DASHBOARD_BASE_URL "${DOMAIN:+https://$DOMAIN}" .env
  set_env CORS_ORIGINS "${DOMAIN:+https://$DOMAIN}${DOMAIN:+,}http://localhost:3000" .env
  set_env PAYMENT_CALLBACK_URL "${BASE}/api/v1/payments/callback" .env

  if [ "$PAYMENT_PROVIDER" != "none" ] && [ -n "$PAYMENT_PROVIDER" ]; then
    set_env PAYMENT_PROVIDER "$PAYMENT_PROVIDER" .env
  fi

  chmod 600 .env
  ok ".env created (chmod 600). Edit it anytime to add gateway keys."
fi

# ---- 5. firewall ------------------------------------------------------------
log "Configuring firewall (UFW)..."
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 80/tcp  >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
if [ -z "$DOMAIN" ]; then
  # No reverse proxy: expose app ports directly.
  ufw allow 8000/tcp >/dev/null 2>&1 || true
  ufw allow 3000/tcp >/dev/null 2>&1 || true
fi
yes | ufw enable >/dev/null 2>&1 || true
ok "Firewall configured."

# ---- 6. build & start -------------------------------------------------------
log "Building images and starting the stack (this can take a few minutes)..."
docker compose up -d --build
ok "Containers started."

log "Waiting for the API to become healthy..."
for i in $(seq 1 60); do
  if docker compose exec -T api curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    ok "API is healthy."; break
  fi
  sleep 3
  [ "$i" -eq 60 ] && warn "API health check timed out; check 'docker compose logs api'."
done

log "Applying database migrations..."
docker compose exec -T api alembic upgrade head && ok "Migrations applied."

# ---- 7. optional Nginx + Let's Encrypt -------------------------------------
if [ -n "$DOMAIN" ]; then
  ask LE_EMAIL "Email for Let's Encrypt (blank = skip SSL)" ""
  log "Installing Nginx..."
  apt-get install -y -qq nginx >/dev/null
  conf=/etc/nginx/sites-available/vpnrobot
  cp -f deploy/nginx/vpnrobot.conf "$conf"
  sed -i "s/example.com/${DOMAIN}/g" "$conf"
  ln -sf "$conf" /etc/nginx/sites-enabled/vpnrobot
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
  ok "Nginx reverse proxy configured for ${DOMAIN}."
  if [ -n "$LE_EMAIL" ]; then
    apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
    if certbot --nginx -d "$DOMAIN" --redirect --agree-tos -m "$LE_EMAIL" --non-interactive; then
      ok "TLS certificate installed; auto-renewal enabled."
    else
      warn "Certbot failed (DNS not pointed to this server yet?). Re-run later: certbot --nginx -d $DOMAIN"
    fi
  fi
fi

# ---- 8. nightly backups -----------------------------------------------------
if [ -f deploy/backup.sh ]; then
  chmod +x deploy/backup.sh
  cron_line="30 3 * * * cd $APP_DIR && bash deploy/backup.sh >> /var/log/vpnrobot-backup.log 2>&1"
  ( crontab -l 2>/dev/null | grep -v 'vpnrobot/deploy/backup.sh' ; echo "$cron_line" ) | crontab - 2>/dev/null \
    && ok "Nightly backup cron installed (03:30)." || warn "Could not install backup cron."
fi

# ---- 9. first dashboard admin ----------------------------------------------
echo
ask        ADMIN_EMAIL    "Create dashboard admin — email (blank = skip)" ""
if [ -n "$ADMIN_EMAIL" ]; then
  ask_secret ADMIN_PASSWORD "Dashboard admin password"
  if [ -n "$ADMIN_PASSWORD" ]; then
    docker compose exec -T api python -m app.cli create-admin \
      --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" --role super_admin --name "Owner" \
      && ok "Dashboard admin created: $ADMIN_EMAIL" || warn "Admin creation failed (maybe already exists)."
  fi
fi

# ---- 10. summary ------------------------------------------------------------
echo
ok "Installation complete!"
echo "──────────────────────────────────────────────"
if [ -n "$DOMAIN" ]; then
  echo "  Dashboard : https://${DOMAIN}"
  echo "  API docs  : https://${DOMAIN}/docs"
else
  IP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo SERVER_IP)"
  echo "  Dashboard : http://${IP}:3000"
  echo "  API docs  : http://${IP}:8000/docs"
fi
echo "  Project   : $APP_DIR"
echo "  Logs      : docker compose logs -f api customer_bot admin_bot worker"
echo "  Manage    : docker compose ps | restart | down"
echo "──────────────────────────────────────────────"
echo "Open your bots in Telegram and press Start. Edit $APP_DIR/.env for gateway keys, then:"
echo "  docker compose up -d"
