#!/usr/bin/env bash
# ==============================================================================
# Скрыпт стварэння / абнаўлення Cloud Run Job для Clipmaker Worker
# ==============================================================================

set -e

# Параметры па змаўчанні
JOB_NAME="${CLOUD_RUN_JOB_NAME:-clipmaker-render}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
IMAGE="${WORKER_IMAGE:-ghcr.io/tuteishygpt/clipmaker-worker:latest}"
CPU="8"
MEMORY="16Gi"
TIMEOUT="1800s"

echo "=================================================================="
echo "Разгортванне Cloud Run Job: $JOB_NAME"
echo "=================================================================="
echo "Праект GCP:  $PROJECT_ID"
echo "Рэгіён:      $REGION"
echo "Вобраз:      $IMAGE"
echo "Рэсурсы:     $CPU vCPU / $MEMORY RAM"
echo "Таймаўт:     $TIMEOUT"
echo "------------------------------------------------------------------"

if [ -z "$PROJECT_ID" ]; then
    echo "[-] Памылка: PROJECT_ID не вызначаны. Задайце GOOGLE_CLOUD_PROJECT або выканайце 'gcloud config set project'."
    exit 1
fi

# Праверка, ці існуе ўжо гэты Job
if gcloud run jobs describe "$JOB_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1; then
    echo "[*] Job '$JOB_NAME' ужо існуе. Выконваецца абнаўленне канфігурацыі..."
    gcloud run jobs update "$JOB_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --image="$IMAGE" \
        --cpu="$CPU" \
        --memory="$MEMORY" \
        --task-timeout="$TIMEOUT" \
        --max-retries=0
else
    echo "[*] Ствараецца новы Job '$JOB_NAME'..."
    gcloud run jobs create "$JOB_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --image="$IMAGE" \
        --cpu="$CPU" \
        --memory="$MEMORY" \
        --task-timeout="$TIMEOUT" \
        --max-retries=0
fi

echo "=================================================================="
echo "[+] Cloud Run Job '$JOB_NAME' паспяхова сканфігураваны!"
echo "    Каб праверыць тэставы запуск, выканайце:"
echo "    gcloud run jobs execute $JOB_NAME --args='--project_id=test_123' --region=$REGION"
echo "=================================================================="
