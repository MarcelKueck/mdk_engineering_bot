# Deployment — Hetzner CX32

This guide installs MDK Engineering Bot on a fresh Hetzner Cloud VPS
behind Caddy with auto-TLS. The whole thing is one Docker Compose stack.

## 1. Provision the VPS

- Hetzner Cloud → **Add Server**
- Type: **CX32** (4 vCPU / 8 GB RAM, sufficient for Phase 0/1)
- OS: **Ubuntu 24.04 LTS**
- Add your SSH key
- Note the IPv4 address

## 2. DNS

Point an A record at the VPS IP, e.g.

```
bot.your-domain.de  A  <vps-ip>  300
```

Wait for the record to propagate (`dig bot.your-domain.de +short`).

## 3. Harden the box

```bash
ssh root@<vps-ip>

# Create non-root user
adduser --disabled-password --gecos "" mdk
usermod -aG sudo mdk
mkdir -p /home/mdk/.ssh
cp ~/.ssh/authorized_keys /home/mdk/.ssh/
chown -R mdk:mdk /home/mdk/.ssh
chmod 700 /home/mdk/.ssh && chmod 600 /home/mdk/.ssh/authorized_keys

# SSH: disable root + password auth
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Unattended security updates
apt-get update && apt-get install -y unattended-upgrades fail2ban
dpkg-reconfigure -plow unattended-upgrades
systemctl enable --now fail2ban
```

## 4. Install Docker

```bash
ssh mdk@<vps-ip>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker mdk
exit
ssh mdk@<vps-ip>   # re-login so the group takes effect
docker compose version
```

## 5. Deploy the application

```bash
sudo mkdir -p /opt/mdk_bot
sudo chown mdk:mdk /opt/mdk_bot
cd /opt/mdk_bot
git clone https://github.com/marcelkueck/mdk_engineering_bot.git .

cp .env.example .env
# Edit .env. At minimum, set:
#   ENVIRONMENT=production
#   SECRET_KEY                = python -c "import secrets; print(secrets.token_urlsafe(64))"
#   WEB_SESSION_TOKEN         = a long random string (you'll type this to log in)
#   INTERNAL_API_TOKEN        = another long random string
#   MASTER_ENCRYPTION_KEY     = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   POSTGRES_PASSWORD         = another long random string
#   DATABASE_URL              = postgresql+asyncpg://mdk:<pw>@db:5432/mdk
#   DATABASE_URL_SYNC         = postgresql+psycopg://mdk:<pw>@db:5432/mdk
#   TELEGRAM_BOT_TOKEN        = from @BotFather
#   AUTHORIZED_TELEGRAM_USER_ID = your numeric Telegram id (ask @userinfobot)
#   BOT_DOMAIN                = bot.your-domain.de

docker compose -f docker-compose.prod.yml up -d
```

Caddy will request a Let's Encrypt cert automatically the first time the
domain is reached. Verify with:

```bash
docker compose -f docker-compose.prod.yml logs -f caddy
```

## 6. Run migrations

```bash
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head
```

## 7. Verify

- Visit `https://bot.your-domain.de/web/login` — log in with `WEB_SESSION_TOKEN`.
- Open Telegram, send `/start` to your bot — it should reply with the
  command list.
- Send `/upcoming 5` — should list the next obligations once the scheduler
  has run once (it runs daily at `DAILY_CHECK_HOUR`, default 08:00). You can
  trigger it manually:

  ```bash
  docker compose -f docker-compose.prod.yml exec scheduler uv run python -c "
  import asyncio
  from mdk_bot.scheduler.jobs import daily_check_job
  asyncio.run(daily_check_job())
  "
  ```

## 8. Backups

Nightly `pg_dump` into a host-mounted directory, uploaded to Hetzner Object
Storage.

```bash
# /opt/mdk_bot/backup.sh
#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p /opt/mdk_bot/backups
docker compose -f /opt/mdk_bot/docker-compose.prod.yml exec -T db \
  pg_dump -U mdk mdk | gzip > "/opt/mdk_bot/backups/mdk-${TS}.sql.gz"
# Keep last 30
find /opt/mdk_bot/backups -name "mdk-*.sql.gz" -mtime +30 -delete

# (optional) upload to Hetzner Object Storage via rclone:
# rclone copy "/opt/mdk_bot/backups/mdk-${TS}.sql.gz" hetzner:mdk-backups/
```

Install as a systemd timer or cron:

```bash
sudo chmod +x /opt/mdk_bot/backup.sh
echo "0 3 * * * mdk /opt/mdk_bot/backup.sh >> /var/log/mdk-backup.log 2>&1" \
  | sudo tee /etc/cron.d/mdk-backup
```

## 9. Updating

```bash
cd /opt/mdk_bot
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head
```

## 9b. Enabling Phase 2 capabilities

Phase 2 adds finance automation behind feature flags. Each module needs
its flag set to `true` AND its credential present, otherwise it logs a
"skipped" line and the bot/scheduler/API stay healthy.

```bash
# After deploying, edit .env to opt into the modules you want:
# Lexware sync:        FEATURE_LEXWARE_SYNC=true  + LEXWARE_API_KEY
# UStVA preparation:   FEATURE_USTVA=true
# Liquidity:           FEATURE_LIQUIDITY=true     + LIQUIDITY_OPENING_BALANCE
# Mahnwesen:           FEATURE_DUNNING=true       (review BASISZINSSATZ each Jan/Jul!)
# VIES validation:     FEATURE_VIES=true          + VIES_REQUESTER_VAT_ID
# DATEV export:        FEATURE_DATEV=true

# Apply the migration that adds the new tables:
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head

# Restart the stack so the new flags take effect:
docker compose -f docker-compose.prod.yml restart api bot scheduler
```

After the migration runs, the five seed `RecurringExpense` rows
(Claude, Lebara, Lexware Office, Google Workspace, Hetzner) will be
visible at `/web/expenses` and via `/expenses` in Telegram.

Persist `./data/datev/` and `./data/vies/` if you enable the DATEV or
VIES modules — they write PDF / CSV artifacts there. Mount them as a
named Docker volume if you use the prod compose file.

See [PHASE2.md](./PHASE2.md) for module-by-module configuration.

## 10. Troubleshooting

```bash
# Live logs
docker compose -f docker-compose.prod.yml logs -f api bot scheduler

# Restart a single service
docker compose -f docker-compose.prod.yml restart bot

# Inspect the DB
docker compose -f docker-compose.prod.yml exec db psql -U mdk mdk

# Manually run the daily check
docker compose -f docker-compose.prod.yml exec scheduler \
  uv run python -c "import asyncio; from mdk_bot.scheduler.jobs import daily_check_job; asyncio.run(daily_check_job())"
```
