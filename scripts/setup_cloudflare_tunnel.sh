#!/usr/bin/env bash
# ==============================================================================
# Скрыпт усталёўкі і налады Cloudflare Tunnel на e2-micro VM
# ==============================================================================
# Дазваляе атрымаць паўнавартасны вонкавы HTTPS-дамен да лакальнага FastAPI
# цалкам бясплатна (0$), без набыцця вонкавага IPv4 і без платнага Cloud NAT!
# ==============================================================================

set -e

echo "=================================================================="
echo "Налада Cloudflare Tunnel (cloudflared)"
echo "=================================================================="

# 1. Спампоўка і ўсталёўка cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "[*] Спампоўка і ўстаноўка афіцыйнага deb-пакета cloudflared..."
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i cloudflared.deb
    rm cloudflared.deb
    echo "[+] cloudflared паспяхова ўсталяваны!"
else
    echo "[*] cloudflared ужо ўсталяваны."
fi

echo "------------------------------------------------------------------"
echo "КРОК 1: Аўтарызацыя ў Cloudflare"
echo "Выканайце наступную каманду і адкрыйце спасылку ў браўзеры:"
echo "    cloudflared tunnel login"
echo "------------------------------------------------------------------"
echo "КРОК 2: Стварэнне тунэля"
echo "    cloudflared tunnel create clipmaker-api"
echo "------------------------------------------------------------------"
echo "КРОК 3: Прывязка дамена (DNS Route)"
echo "    cloudflared tunnel route dns clipmaker-api api.yourdomain.com"
echo "------------------------------------------------------------------"
echo "КРОК 4: Запуск як сістэмнага сэрвісу (Systemd Daemon)"
echo "    sudo cloudflared service install"
echo "    sudo systemctl enable --now cloudflared"
echo "=================================================================="
