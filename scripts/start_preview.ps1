<#
  Clinic operations preview launcher (Windows PowerShell 5.1+ / 7).

  One-command Product Owner workflow:
    1) Resolve repo + venv
    2) Check Docker readiness BEFORE expensive prepare/build
    3) Reuse dependency/build cache
    4) Start disposable PG15 + API + panel with rich demo seed
    5) Open the default browser to the current PANEL_URL (unless -NoBrowser)

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
    powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1 -Force
    powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1 -NoBrowser
#>
param(
  [switch]$Force,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "Repository: $repo"

function Wait-DockerReady {
  param([int]$Attempts = 12, [int]$DelaySeconds = 5)
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error @"
Docker CLI was not found on PATH.
Install/start Docker Desktop, ensure it is healthy, then re-run:
  powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
Do not bypass security settings or kill unrelated containers.
"@
    exit 2
  }
  for ($i = 1; $i -le $Attempts; $i++) {
    docker info 1>$null 2>$null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Docker engine is ready."
      return
    }
    Write-Host "Docker not ready (attempt $i/$Attempts). Waiting ${DelaySeconds}s ..."
    Start-Sleep -Seconds $DelaySeconds
  }
  Write-Error @"
Docker Desktop is not available or not ready after $Attempts attempts.
Start Docker Desktop, wait until the engine is healthy, then re-run this script.
Do not bypass security settings or kill unrelated containers.
"@
  exit 2
}

Write-Host "Checking Docker Desktop readiness before prepare/build ..."
Wait-DockerReady

$venvPython = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Write-Host "Creating .venv ..."
  python -m venv .venv
}
if (-not (Test-Path $venvPython)) {
  Write-Error "Virtual environment Python was not found at $venvPython"
  exit 2
}

$env:PYTHONPATH = "$repo\src;$repo"
# Disposable ACR-D0.11 ops schema for full-operations preview (never official Alembic).
$env:CLINIC_OPS_SCHEMA_MODE = "disposable"
if (-not $env:CLINIC_DEMO_PROFILE) { $env:CLINIC_DEMO_PROFILE = "demo" }
if ($NoBrowser) {
  $env:CLINIC_PREVIEW_NO_BROWSER = "1"
} else {
  Remove-Item Env:CLINIC_PREVIEW_NO_BROWSER -ErrorAction SilentlyContinue
}

$prepare = @("scripts\prepare_preview.py")
if ($Force) { $prepare += "--force" }
Write-Host "Preparing cached dependencies/build ..."
& $venvPython @prepare
if ($LASTEXITCODE -ne 0) { throw "prepare_preview failed" }

Write-Host "Validating Asia/Tehran timezone support in .venv (requires tzdata on Windows) ..."
& $venvPython scripts\check_tehran_timezone.py
if ($LASTEXITCODE -ne 0) {
  Write-Host "Timezone preflight failed; forcing dependency reinstall so tzdata is installed ..."
  & $venvPython scripts\prepare_preview.py --force
  if ($LASTEXITCODE -ne 0) { throw "prepare_preview --force failed after timezone preflight" }
  & $venvPython scripts\check_tehran_timezone.py
  if ($LASTEXITCODE -ne 0) {
    Write-Error @"
Asia/Tehran is still unavailable after dependency repair.
Install tzdata into the repository virtual environment, then re-run:
  .\.venv\Scripts\python.exe -m pip install -e `".[dev]`"
  powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
"@
    exit 2
  }
}
Write-Host "Timezone preflight OK (Asia/Tehran)."

Write-Host "Starting the preview stack (Ctrl+C stops it and deletes disposable data) ..."
& $venvPython scripts\start_preview_stack.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
