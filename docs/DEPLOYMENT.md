# Production Deployment Guide (Ubuntu Server)

Target: **Ubuntu 22.04/24.04 LTS**, a domain you control, and root/sudo access.
All commands are copy-paste ready. Replace `example.com` and secrets accordingly.

Topology behind Nginx + Let's Encrypt:

```
Internet ──443──▶ Nginx (host) ──▶ frontend:3000 (dashboard, /)
                              └──▶ api:8000      (/api, /docs)
docker network: postgres, redis, worker, beat, customer_bot, admin_bot
```

---

## 1. Server preparation

```bash
sudo apt update && sudo apt -y upgrade
sudo timedatectl set-timezone Asia/Tehran
sudo apt -y install git ufw fail2ban curl ca-certificates

# Dedicated non-root deploy user
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG sudo deploy
```

## 2. Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

`fail2ban` is enabled by default and protects SSH. Verify: `sudo systemctl status fail2ban`.

## 3. Docker & Compose

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy        # log out/in for group to take effect
docker --version && docker compose version
sudo systemctl enable --now docker
```

## 4. Clone & configure

```bash
sudo mkdir -p /opt/vpnrobot && sudo chown deploy:deploy /opt/vpnrobot
cd /opt/vpnrobot
git clone <your-repo-url> .
cp .env.example .env

# Generate strong secrets
echo "SECRET_KEY=$(openssl rand -hex 32)"          >> .env.secrets
echo "JWT_REFRESH_SECRET_KEY=$(openssl rand -hex 32)" >> .env.secrets
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"   >> .env.secrets
```

Edit `.env` and set, at minimum:

- `ENVIRONMENT=production`, `DEBUG=false`
- `SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `POSTGRES_PASSWORD` (from above)
- `DATABASE_URL` (use the same password)
- `CUSTOMER_BOT_TOKEN`, `ADMIN_BOT_TOKEN`, `BOOTSTRAP_SUPER_ADMINS=<your-tg-id>`
- `API_BASE_URL=https://example.com`, `DASHBOARD_BASE_URL=https://example.com`
- `CORS_ORIGINS=https://example.com`
- `PAYMENT_PROVIDER` + the matching gateway keys, `PAYMENT_CALLBACK_URL=https://example.com/api/v1/payments/callback`

> Keep `.env` out of git (it already is). Restrict perms: `chmod 600 .env`.

## 5. Build & start the stack

```bash
docker compose up -d --build
docker compose ps
# Migrations run automatically via the api service command; or run manually:
docker compose exec api alembic upgrade head
```

Create the first web-dashboard admin (the bootstrap admins can only use the bot):

```bash
docker compose exec api python -m app.cli create-admin \
  --email you@example.com --password 'a-strong-password' --role super_admin --name "Owner"
```

## 6. Nginx reverse proxy + SSL

```bash
sudo apt -y install nginx certbot python3-certbot-nginx
sudo cp deploy/nginx/vpnrobot.conf /etc/nginx/sites-available/vpnrobot
sudo sed -i 's/example.com/YOURDOMAIN/g' /etc/nginx/sites-available/vpnrobot
sudo ln -sf /etc/nginx/sites-available/vpnrobot /etc/nginx/sites-enabled/vpnrobot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Obtain + install certificate (auto-edits the vhost for 443)
sudo certbot --nginx -d example.com --redirect --agree-tos -m you@example.com --non-interactive
```

Certbot installs a systemd timer for automatic renewal. Verify:

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

## 7. Telegram bots & DNS

- Point an `A` record for `example.com` to the server IP.
- The bots run in long-polling mode by default (`USE_WEBHOOK=false`) — no inbound
  ports required. Confirm they came up:

```bash
docker compose logs -f customer_bot admin_bot
```

## 8. Smoke test

```bash
curl -fsS https://example.com/api/v1/../health   # -> {"status":"ok",...}
curl -fsS https://example.com/api/v1/auth/login -X POST \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"a-strong-password"}'
```

Open `https://example.com` → dashboard login. Open the customer bot in Telegram,
press Start, and walk through a purchase.

---

## 9. Monitoring

See [`MONITORING.md`](MONITORING.md). Quick start:

```bash
docker compose ps                       # container health (healthchecks defined)
docker compose logs -f --tail=100 api worker beat
docker stats                            # live resource usage
```

Structured JSON logs ship to stdout; aggregate with Loki/Promtail, Vector, or your
platform's log driver. `/health` is a cheap liveness probe for uptime monitors.

## 10. Backups

See [`BACKUP.md`](BACKUP.md). Install the nightly DB + media backup cron:

```bash
sudo cp deploy/backup.sh /opt/vpnrobot/deploy/backup.sh
chmod +x /opt/vpnrobot/deploy/backup.sh
( crontab -l 2>/dev/null; echo "30 3 * * * /opt/vpnrobot/deploy/backup.sh >> /var/log/vpnrobot-backup.log 2>&1" ) | crontab -
```

## 11. Updates / redeploy

```bash
cd /opt/vpnrobot
git pull
docker compose up -d --build
docker compose exec api alembic upgrade head
docker image prune -f
```

Zero-config rollback: check out the previous tag and rebuild; migrations are
forward-only, so take a DB backup before upgrading (the backup script does this).

## 12. Production hardening checklist

- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] All secrets random & 32+ bytes; `.env` is `chmod 600`, never committed
- [ ] Postgres/Redis are **not** published to the host (only `api`/`frontend` ports
      are; in `docker-compose.yml` they sit on the internal network) — confirm with
      `sudo ss -tlnp` that only 80/443/22 are externally reachable
- [ ] `ufw` enabled; `fail2ban` running
- [ ] Automatic security updates: `sudo apt -y install unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades`
- [ ] HTTPS enforced (certbot `--redirect`); HSTS set in the Nginx config
- [ ] Nightly backups verified and copied off-box (S3/rsync)
- [ ] Bot tokens rotated if ever exposed; `BOOTSTRAP_SUPER_ADMINS` limited
- [ ] Rate limiting active (`RATE_LIMIT_PER_MINUTE`) and Nginx `limit_req` zone on `/api`
