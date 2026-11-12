# Create the shared Stage 4 services virtual environment and install deps.
#
# All four services share one venv for local convenience; they still run as
# independent processes with independent stores. Nothing here starts a service.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root "services\.venv"

if (-not (Test-Path $venv)) {
    Write-Host "Creating venv at $venv..."
    python -m venv $venv
}

$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root "services\requirements.txt")
& $python -m pip install -e (Join-Path $root "services\contracts")

Write-Host "Setup complete. Start the stack with scripts\start-stack.ps1"
