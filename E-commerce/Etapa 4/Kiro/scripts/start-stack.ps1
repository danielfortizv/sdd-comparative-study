# Start the full Stage 4 distributed stack locally (PowerShell, Windows).
#
# Starts the four backend processes (identity, commerce, reviews, gateway) from
# the shared services venv, each on its tool-isolated port from
# stage4-runtime.json, against the real RabbitMQ broker running in WSL.
#
# The broker is assumed already running and provisioned (see the README note);
# this script does NOT start RabbitMQ. Service/broker addresses are environment
# based with defaults from stage4-runtime.json.
#
# Readiness is checked deterministically by polling each /health endpoint (and,
# for the frontend, its HTTP root). Each started process is recorded immediately
# in .stage4-pids.json -- with its process name and start time so stop-stack.ps1
# can guard against stale/reused PIDs and kill exactly the processes this script
# owns. If any step fails, the processes started so far are cleaned up before
# the error propagates (no orphaned partial-start children).
#
# All processes are launched hidden with their stdout/stderr redirected to log
# files under logs/; no -NoNewWindow console-handle inheritance is used.
#
# Usage:
#   .\scripts\start-stack.ps1            # start backend services + gateway
#   .\scripts\start-stack.ps1 -Frontend # additionally start the frontend (Vite)

param(
    [switch]$Frontend
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtime = Get-Content (Join-Path $root "stage4-runtime.json") | ConvertFrom-Json
$python = Join-Path $root "services\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Shared venv not found at $python. Create it with scripts\setup.ps1 first."
}

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$pidFile = Join-Path $root ".stage4-pids.json"

# Deployment parameters from stage4-runtime.json -> environment.
$env:GATEWAY_PORT = $runtime.gateway_port
$env:IDENTITY_PORT = $runtime.identity_port
$env:COMMERCE_PORT = $runtime.commerce_port
$env:REVIEWS_PORT = $runtime.reviews_port
$env:FRONTEND_PORT = $runtime.frontend_port
$env:AMQP_URL = $runtime.amqp_url
$env:EVENT_NAMESPACE = $runtime.event_namespace
$env:IDENTITY_URL = "http://127.0.0.1:$($runtime.identity_port)"
$env:COMMERCE_URL = "http://127.0.0.1:$($runtime.commerce_port)"
$env:REVIEWS_URL = "http://127.0.0.1:$($runtime.reviews_port)"
# Per-service owned stores under services/<name>/.
$env:IDENTITY_DB_PATH = Join-Path $root "services\identity\identity.db"
$env:COMMERCE_DB_PATH = Join-Path $root "services\commerce\commerce.db"
$env:REVIEWS_DB_PATH = Join-Path $root "services\reviews\reviews.db"
$env:REVIEW_IMAGE_DIR = Join-Path $root "services\reviews\review_images"

# Owned-process records: one entry per spawned process, carrying enough identity
# (pid + process name + start time) for stop-stack.ps1 to reject stale/reused PIDs.
$owned = [System.Collections.ArrayList]::new()

function Save-Owned {
    # Persist the owned-process records immediately so a crash mid-start still
    # leaves a pid file the user (or stop-stack) can act on.
    $owned | ConvertTo-Json -Depth 4 | Set-Content $pidFile
}

function Register-Owned($name, $proc) {
    $record = [ordered]@{
        name        = $name
        pid         = $proc.Id
        processName = $proc.ProcessName
        startTime   = $proc.StartTime.ToString("o")
    }
    [void]$owned.Add($record)
    Save-Owned
}

function Stop-Owned {
    # Best-effort cleanup of every process started so far (used on failure).
    foreach ($record in $owned) {
        $p = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
        if ($p) {
            taskkill /PID $record.pid /T /F 2>$null | Out-Null
        }
    }
}

function Start-BackendService($name, $cwd, $port) {
    Write-Host "Starting $name on port $port..."
    $outLog = Join-Path $logDir "$name.out.log"
    $errLog = Join-Path $logDir "$name.err.log"
    $proc = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$port") `
        -WorkingDirectory $cwd -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Register-Owned $name $proc
    return $proc
}

function Start-Frontend($cwd, $port) {
    Write-Host "Starting frontend (Vite dev) on port $port..."
    # npm.cmd is a batch shim that Start-Process cannot exec directly on Windows
    # (it raises "%1 is not a valid Win32 application"). Launch the installed
    # node executable against Vite's local JS entry instead, quoting paths with
    # spaces so a workspace under e.g. "OneDrive\Escritorio\..." still resolves.
    $node = (Get-Command node -ErrorAction Stop).Source
    $viteEntry = Join-Path $cwd "node_modules\vite\bin\vite.js"
    if (-not (Test-Path $viteEntry)) {
        throw "Vite entry not found at $viteEntry. Run 'npm install' in frontend first."
    }
    $outLog = Join-Path $logDir "frontend.out.log"
    $errLog = Join-Path $logDir "frontend.err.log"
    # Bind Vite to 127.0.0.1 explicitly: its default "localhost" resolves to ::1
    # (IPv6) on this host, which the IPv4 readiness poll below never reaches.
    $proc = Start-Process -FilePath $node `
        -ArgumentList @("`"$viteEntry`"", "--host", "127.0.0.1", "--port", "$port", "--strictPort") `
        -WorkingDirectory $cwd -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    Register-Owned "frontend" $proc
    return $proc
}

function Wait-Ready($name, $url) {
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                Write-Host "  $name is ready."
                return
            }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    throw "$name did not become ready at $url"
}

function Wait-Healthy($name, $port) {
    Wait-Ready $name "http://127.0.0.1:$port/health"
}

try {
    Start-BackendService "identity" (Join-Path $root "services\identity") $runtime.identity_port | Out-Null
    Start-BackendService "commerce" (Join-Path $root "services\commerce") $runtime.commerce_port | Out-Null
    Start-BackendService "reviews" (Join-Path $root "services\reviews") $runtime.reviews_port | Out-Null

    Wait-Healthy "identity" $runtime.identity_port
    Wait-Healthy "commerce" $runtime.commerce_port
    Wait-Healthy "reviews" $runtime.reviews_port

    Start-BackendService "gateway" (Join-Path $root "services\gateway") $runtime.gateway_port | Out-Null
    Wait-Healthy "gateway" $runtime.gateway_port

    if ($Frontend) {
        Start-Frontend (Join-Path $root "frontend") $runtime.frontend_port | Out-Null
        Wait-Ready "frontend" "http://127.0.0.1:$($runtime.frontend_port)/"
    }
}
catch {
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Cleaning up partially started processes..."
    Stop-Owned
    if (Test-Path $pidFile) { Remove-Item $pidFile -Force }
    throw
}

Write-Host ""
Write-Host "Stage 4 stack is up."
Write-Host "  Gateway:  http://127.0.0.1:$($runtime.gateway_port)"
if ($Frontend) { Write-Host "  Frontend: http://127.0.0.1:$($runtime.frontend_port)" }
Write-Host "Logs are under $logDir"
Write-Host "Stop it with: .\scripts\stop-stack.ps1"
