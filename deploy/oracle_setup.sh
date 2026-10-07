#!/usr/bin/env bash
# One-shot setup for the India News Bot on an Oracle Cloud Always Free VM
# (Ubuntu 22.04 / 24.04 - ARM A1 or x86 E2.1.Micro, both fine).
#
# Usage on the fresh VM, inside the project folder:
#   bash deploy/oracle_setup.sh
set -euo pipefail

echo "==> Installing Docker and git..."
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 git

echo "==> Adding $USER to the docker group (for convenience)..."
sudo usermod -aG docker "$USER" || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo
  echo "==> .env not found in $PROJECT_DIR."
  echo "    Create it now - paste your secrets (3 lines), save (Ctrl+O, Enter), exit (Ctrl+X):"
  echo "      TELEGRAM_BOT_TOKEN=..."
  echo "      TELEGRAM_FREE_CHANNEL=@indian_news_nationalist"
  echo "      DEEPSEEK_API_KEY=..."
  nano .env
fi

echo "==> Building and starting the bot (24x7, auto-restart)..."
sudo docker compose up -d --build

echo
echo "==> Done! Your bot now runs in the cloud. Latest logs:"
sudo docker compose logs --tail 30
echo
echo "Handy commands:"
echo "  sudo docker compose logs -f      # live logs"
echo "  sudo docker compose restart      # restart the bot"
echo "  sudo docker compose down         # stop everything"
echo
echo "IMPORTANT: never run the bot on your PC at the same time (one instance only)."
