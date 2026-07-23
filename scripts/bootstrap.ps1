# Bootstrap the local telemetry analytics stack end-to-end.
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$EnvFile = ".env"
$TelemetryFile = "data/raw/telemetry_logs.jsonl"
$EmployeesFile = "data/raw/employees.csv"

if (-not (Test-Path $EnvFile)) {
    Write-Host "Creating $EnvFile from .env.example"
    Copy-Item ".env.example" $EnvFile
}

Write-Host "Starting Docker Compose stack..."
docker compose --env-file $EnvFile up --build -d

Write-Host "Waiting for PostgreSQL to become healthy..."
do {
    Start-Sleep -Seconds 2
    $ready = docker compose exec -T postgres pg_isready -U telemetry -d telemetry 2>$null
} while ($LASTEXITCODE -ne 0)

Write-Host "Applying database migrations..."
docker compose exec -T api alembic upgrade head

if (-not (Test-Path $TelemetryFile)) {
    Write-Host "Generating sample telemetry and employee data..."
    docker compose exec -T api python generate_fake_data.py
}

Write-Host "Loading telemetry into PostgreSQL..."
docker compose exec -T api python -m etl.run load `
    --input $TelemetryFile `
    --employees $EmployeesFile

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "  API docs:    http://localhost:8000/docs"
Write-Host "  Health:      http://localhost:8000/health"
Write-Host "  Dashboard:   http://localhost:8501"
Write-Host ""
Write-Host "Verify: curl http://localhost:8000/analytics/overview"
