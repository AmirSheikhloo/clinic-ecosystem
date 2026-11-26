<#
  Simple repeatable preview start for Windows (PowerShell 5.1+ / 7).
  Creates .venv on first use, installs/builds only when inputs changed, then starts the
  disposable PostgreSQL 15 + API + Next.js stack. Docker Desktop must be running.

  Usage:   powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
           powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1 -Force   # rebuild everything
#>
param([switch]$Force)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$venvPython = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Write-Host "Creating .venv ..."
  python -m venv .venv
}

$env:PYTHONPATH = "$repo\src;$repo"
$prepare = @("scripts\prepare_preview.py")
if ($Force) { $prepare += "--force" }
& $venvPython @prepare
if ($LASTEXITCODE -ne 0) { throw "prepare_preview failed" }

Write-Host "Checking Docker Desktop readiness ..."
docker info 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Error @"
Docker Desktop is not available or not ready.
Start Docker Desktop, wait until the engine is healthy, then re-run:
  powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
Do not bypass security settings or kill unrelated containers.
"@
  exit 2
}

Write-Host "Starting the preview stack (Ctrl+C stops it and deletes all data) ..."
& $venvPython scripts\start_preview_stack.py
