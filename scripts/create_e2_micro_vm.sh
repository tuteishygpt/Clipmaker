#!/usr/bin/env bash
# ==============================================================================
# Скрыпт стварэння 100% Free Tier віртуальнай машыны e2-micro ў GCP
# ==============================================================================
# ПАПЯРЭДЖАННЕ АБ БІЛІНГУ:
# 1. Рэгіён: ТОЛЬКІ us-central1, us-east1 альбо us-west1 (Always Free).
# 2. Дыск: ТОЛЬКІ pd-standard (не SSD і не Balanced!), памерам да 30 GB.
# 3. Сетка: БЕЗ вонкавага IPv4 (--no-address), але з бясплатным вонкавым IPv6!
# ==============================================================================

set -e

VM_NAME="${VM_NAME:-clipmaker-api}"
ZONE="${GCP_ZONE:-us-central1-a}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
MACHINE_TYPE="e2-micro"
DISK_SIZE="30GB"
DISK_TYPE="pd-standard"
IMAGE_FAMILY="ubuntu-2404-lts-amd64"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "=================================================================="
echo "Стварэнне Always Free VM: $VM_NAME"
echo "=================================================================="
echo "Праект:      $PROJECT_ID"
echo "Зона:        $ZONE"
echo "Тып машыны:  $MACHINE_TYPE (2 vCPU burst, 1 GB RAM)"
echo "Дыск:        $DISK_SIZE ($DISK_TYPE)"
echo "Сетка:       Dual-Stack (IPv6 знешні, БЕЗ платнага IPv4)"
echo "------------------------------------------------------------------"

# 1. Уключэнне Compute Engine API пры неабходнасці
echo "[*] Праверка Compute Engine API..."
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"

# 2. Стварэнне інстанса
echo "[*] Стварэнне віртуальнай машыны $VM_NAME..."
gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --network-interface=stack-type=IPV4_IPV6,ipv6-network-tier=PREMIUM,no-address \
    --create-boot-disk=auto-delete=yes,boot=yes,image-family="$IMAGE_FAMILY",image-project="$IMAGE_PROJECT",size="$DISK_SIZE",type="$DISK_TYPE" \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=clipmaker-api

echo "=================================================================="
echo "[+] Віртуальная машына '$VM_NAME' паспяхова створана!"
echo "    Падключэнне праз gcloud SSH:"
echo "    gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID"
echo "=================================================================="
