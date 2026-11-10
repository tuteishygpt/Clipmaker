# ==============================================================================
# PowerShell скрыпт стварэння / абнаўлення Cloud Run Job для Clipmaker Worker
# ==============================================================================

param (
    [string]$JobName = $env:CLOUD_RUN_JOB_NAME,
    [string]$Region = $env:GOOGLE_CLOUD_LOCATION,
    [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
    [string]$Image = $env:WORKER_IMAGE
)

if (-not $JobName) { $JobName = "clipmaker-render" }
if (-not $Region) { $Region = "us-central1" }
if (-not $ProjectId) { $ProjectId = (gcloud config get-value project 2>$null).Trim() }
if (-not $Image) { $Image = "ghcr.io/tuteishygpt/clipmaker-worker:latest" }

$Cpu = "8"
$Memory = "16Gi"
$Timeout = "1800s"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Разгортванне Cloud Run Job: $JobName" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Праект GCP:  $ProjectId"
Write-Host "Рэгіён:      $Region"
Write-Host "Вобраз:      $Image"
Write-Host "Рэсурсы:     $Cpu vCPU / $Memory RAM"
Write-Host "Таймаўт:     $Timeout"
Write-Host "------------------------------------------------------------------"

if (-not $ProjectId) {
    Write-Host "[-] Памылка: ProjectId не вызначаны. Задайце GOOGLE_CLOUD_PROJECT або выканайце 'gcloud config set project'." -ForegroundColor Red
    exit 1
}

# Праверка, ці існуе Job
$jobExists = $false
try {
    $describeOutput = gcloud run jobs describe $JobName --project=$ProjectId --region=$Region 2>&1
    if ($LASTEXITCODE -eq 0) {
        $jobExists = $true
    }
} catch {
    $jobExists = $false
}

if ($jobExists) {
    Write-Host "[*] Job '$JobName' ужо існуе. Выконваецца абнаўленне..." -ForegroundColor Yellow
    gcloud run jobs update $JobName `
        --project=$ProjectId `
        --region=$Region `
        --image=$Image `
        --cpu=$Cpu `
        --memory=$Memory `
        --task-timeout=$Timeout `
        --max-retries=0
} else {
    Write-Host "[*] Ствараецца новы Job '$JobName'..." -ForegroundColor Green
    gcloud run jobs create $JobName `
        --project=$ProjectId `
        --region=$Region `
        --image=$Image `
        --cpu=$Cpu `
        --memory=$Memory `
        --task-timeout=$Timeout `
        --max-retries=0
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "==================================================================" -ForegroundColor Green
    Write-Host "[+] Cloud Run Job '$JobName' паспяхова сканфігураваны!" -ForegroundColor Green
    Write-Host "    Каб праверыць тэставы запуск, выканайце:"
    Write-Host "    gcloud run jobs execute $JobName --args='--project_id=test_123' --region=$Region"
    Write-Host "==================================================================" -ForegroundColor Green
} else {
    Write-Host "[-] Памылка пры наладзе Cloud Run Job." -ForegroundColor Red
}
