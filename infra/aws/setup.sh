#!/usr/bin/env bash
# EC2 (Ubuntu 22.04) ilk kurulum scripti
# Kullanım: ssh ubuntu@<IP> 'curl -sL https://raw.githubusercontent.com/muzafferberkesavas/financial-llm-production/main/infra/aws/setup.sh | sudo bash'

set -euo pipefail

REPO_URL="https://github.com/muzafferberkesavas/financial-llm-production.git"
APP_DIR="/home/ubuntu/financial-llm-production"

echo "==> Sistem güncelleme"
apt-get update -y
apt-get upgrade -y
apt-get install -y curl git ca-certificates gnupg lsb-release ufw

echo "==> Docker kurulumu"
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    usermod -aG docker ubuntu
fi

echo "==> Repo clone"
if [ ! -d "$APP_DIR" ]; then
    sudo -u ubuntu git clone "$REPO_URL" "$APP_DIR"
else
    cd "$APP_DIR" && sudo -u ubuntu git pull
fi

echo "==> .env hazırla"
cd "$APP_DIR/infra/aws"
if [ ! -f .env ]; then
    sudo -u ubuntu cp .env.example .env
    chown ubuntu:ubuntu .env
    chmod 600 .env
fi

echo "==> Firewall (UFW)"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Host crontab (host'tan docker exec ile)"
CRON_FILE="/etc/cron.d/finllm"
cat > "$CRON_FILE" <<'CRON'
# FinLLM scheduled pipeline runs (UTC times)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# NASDAQ pre-market: 09:00 UTC weekdays (~04:00 ET)
0 9 * * 1-5 ubuntu cd /home/ubuntu/financial-llm-production/infra/aws && /usr/bin/docker compose exec -T api python /app/scripts/run_funnel.py --market nasdaq --llm claude --mode pre_market >> /var/log/finllm-cron.log 2>&1

# BIST pre-market: 06:30 UTC weekdays (~09:30 TR)
30 6 * * 1-5 ubuntu cd /home/ubuntu/financial-llm-production/infra/aws && /usr/bin/docker compose exec -T api python /app/scripts/run_funnel.py --market bist --llm claude --mode pre_market >> /var/log/finllm-cron.log 2>&1

# Outcome update + Platt retrain: 18:00 UTC daily
0 18 * * * ubuntu cd /home/ubuntu/financial-llm-production/infra/aws && /usr/bin/docker compose exec -T api python /app/scripts/update_outcomes.py >> /var/log/finllm-cron.log 2>&1
CRON
chmod 644 "$CRON_FILE"
touch /var/log/finllm-cron.log
chown ubuntu:ubuntu /var/log/finllm-cron.log

echo ""
echo "================================================================"
echo "✅ Kurulum hazır."
echo ""
echo "Şimdi:"
echo "  1) sudo nano $APP_DIR/infra/aws/.env       # secrets'ı doldur"
echo "  2) cd $APP_DIR/infra/aws"
echo "  3) docker compose up -d --build            # ilk build ~3-5 dk"
echo "  4) docker compose ps"
echo "  5) curl http://localhost:8000/v2/health    # iç sağlık kontrolü"
echo "  6) curl https://\$DOMAIN/v2/health         # dış (SSL hazır olunca)"
echo ""
echo "Log'lar: docker compose logs -f api"
echo "Cron log: tail -f /var/log/finllm-cron.log"
echo "================================================================"
