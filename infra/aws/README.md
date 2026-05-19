# AWS EC2 Deployment Guide — FinLLM

Tek bir EC2 instance üzerinde Docker Compose ile backend + Postgres + Telegram DM bot çalıştırma rehberi.

## Mimari

```
[ User ] → HTTPS → [ Caddy ] → [ FastAPI ] ← → [ Postgres (Docker) ]
                                  ↑
                          [ Telegram DM bot ]
                                  ↑
                       [ Host cron — docker exec ]
```

- **Tek EC2 (t3.small, eu-north-1):** ~$15/ay, AWS kredisi karşılar
- **Postgres:** aynı host'ta Docker volume — backup için pg_dump + S3
- **Caddy:** otomatik Let's Encrypt SSL (nip.io veya kendi domain)
- **Cron'lar:** host crontab → `docker compose exec api python …`

## Adım adım

### 0. EC2 instance yaratma (AWS CLI)

`scripts/aws_provision.sh` script'i (repo root) ile otomatik yaratılır. Manuel için:

```bash
aws ec2 create-key-pair --key-name finllm-key --query 'KeyMaterial' --output text > ~/.ssh/finllm-key.pem
chmod 400 ~/.ssh/finllm-key.pem

aws ec2 create-security-group --group-name finllm-sg --description "FinLLM backend"
aws ec2 authorize-security-group-ingress --group-name finllm-sg --protocol tcp --port 22 --cidr <YOUR_IP>/32
aws ec2 authorize-security-group-ingress --group-name finllm-sg --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name finllm-sg --protocol tcp --port 443 --cidr 0.0.0.0/0

aws ec2 run-instances \
  --image-id ami-0a716d3f3b16d290c \
  --instance-type t3.small \
  --key-name finllm-key \
  --security-group-ids <sg-id> \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=finllm-prod}]'
```

### 1. EC2'ya SSH

```bash
ssh -i ~/.ssh/finllm-key.pem ubuntu@<PUBLIC_IP>
```

### 2. Setup script'i çalıştır

```bash
curl -sL https://raw.githubusercontent.com/muzafferberkesavas/financial-llm-production/main/infra/aws/setup.sh | sudo bash
```

Bu script:
- Docker + Docker Compose kurar
- Repo'yu `/home/ubuntu/financial-llm-production`'a klonlar
- UFW firewall aktive eder (22 + 80 + 443)
- Host crontab'ı (`/etc/cron.d/finllm`) NASDAQ + BIST + outcomes cron'larıyla doldurur

### 3. Secrets'ı doldur

```bash
cd /home/ubuntu/financial-llm-production/infra/aws
sudo nano .env
```

Minimum doldurulması gerekenler:
- `DOMAIN` — `api.finllm.app` veya `<EIP-tireli>.nip.io`
- `POSTGRES_PASSWORD` — güçlü şifre (`openssl rand -base64 32`)
- `ANTHROPIC_API_KEY` — Claude API key
- `API_BEARER_TOKEN` — Vercel ile paylaşılan secret (`openssl rand -hex 32`)

Opsiyonel:
- `FINNHUB_API_KEY` — yoksa RSS fallback
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_NASDAQ`, `TELEGRAM_CHANNEL_BIST`

### 4. Servisleri başlat

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

İlk build ~3-5 dakika sürer. Build bitince Caddy otomatik SSL alır (~30sn). nip.io kullanıyorsan cert direkt çıkar; kendi domain'in varsa önce DNS A kaydını instance'ın elastic IP'sine yönlendir.

### 5. Sağlık kontrolü

```bash
# İçten
curl http://localhost:8000/v2/health

# Dıştan (Caddy SSL üzerinden)
curl https://<DOMAIN>/v2/health
```

### 6. Vercel env vars güncelle

Vercel dashboard → Project → Settings → Environment Variables:
- `BACKEND_API_URL` = `https://<DOMAIN>`
- `API_BEARER_TOKEN` = EC2'da .env'deki ile aynı

### 7. İlk pipeline run (manuel test)

```bash
docker compose exec api python /app/scripts/run_funnel.py --market nasdaq --llm claude --max-tickers 3
```

## Operasyon

### Log
```bash
docker compose logs -f api
tail -f /var/log/finllm-cron.log
```

### Yeniden başlat
```bash
docker compose restart api
```

### Update (yeni commit deploy)
```bash
cd /home/ubuntu/financial-llm-production
git pull
cd infra/aws
docker compose build api
docker compose up -d
```

### DB backup
```bash
docker compose exec postgres pg_dump -U finllm finllm > backup-$(date +%F).sql
# S3'e gönder (opsiyonel):
aws s3 cp backup-$(date +%F).sql s3://finllm-backups/
```

### Instance stop/start (maliyet için)
```bash
# Yerel makinen:
aws ec2 stop-instances --instance-ids <id>
aws ec2 start-instances --instance-ids <id>
```

t3.small **durdurulursa $15/ay yerine $1-2/ay** (sadece EBS storage). Marketing sitesi Vercel'de olduğu için dashboard yine çalışır, sadece /app/* API çağrıları boş döner.

## Maliyet özeti

| Bileşen | Maliyet | Not |
|---------|---------|-----|
| EC2 t3.small (24/7) | ~$15/ay | AWS kredi karşılar |
| EBS 20 GB gp3 | ~$2/ay | |
| Elastic IP (instance'a bağlı) | $0 | bağlıysa bedava |
| Data transfer (out) | ~$0.09/GB | Marketing'den ayrı, küçük |
| **Toplam** | **~$17/ay** | AWS kredisi ile bedava |

Vercel dashboard ücretsiz (Hobby plan).
