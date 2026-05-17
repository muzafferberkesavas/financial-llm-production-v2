#!/usr/bin/env bash
# FinGPT AWS EC2 kurulum scripti — Ubuntu 22.04 + NVIDIA T4 (g4dn.xlarge) için.
# Kullanım: ssh -i key.pem ubuntu@<ip> 'bash -s' < setup_aws.sh
set -euo pipefail

echo ">>> System update"
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip git docker.io nvidia-driver-535

echo ">>> Docker + NVIDIA Container Toolkit"
sudo systemctl enable --now docker
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sudo sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update -y
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo ">>> Klasör + .env"
sudo mkdir -p /opt/fingpt
sudo chown ubuntu:ubuntu /opt/fingpt
cd /opt/fingpt
[ -f .env ] || cp .env.example .env

echo ">>> Build & run"
docker build -t fingpt-server:latest .
docker rm -f fingpt 2>/dev/null || true
docker run -d --name fingpt --restart unless-stopped --gpus all \
  --env-file /opt/fingpt/.env \
  -v fingpt-models:/root/.cache/huggingface \
  -v /opt/fingpt/rag_index:/opt/fingpt/rag_index \
  -p 8080:8080 \
  fingpt-server:latest

echo ">>> Done. /health'i kontrol et:"
echo "    curl http://localhost:8080/health"
