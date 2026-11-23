# Stage 3 - Continuous Integration PowerShell Pipeline Script
# Purpose: Installs dependencies, runs backend/frontend tests with coverage, builds frontend, runs Playwright E2E tests, and cleans up.

$ErrorActionPreference = "Stop"
$InitialDirectory = Get-Location

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "          STAGE 3 CONTINUOUS INTEGRATION          " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Helper function to stop a process and all of its children recursively
function Stop-ProcessTree {
    param(
        [Parameter(Mandatory=$true)]
        [int]$ParentPid
    )
    try {
        # Query children using Get-CimInstance or Get-WmiObject
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentPid" -ErrorAction SilentlyContinue
        if (-not $children) {
            $children = Get-WmiObject Win32_Process -Filter "ParentProcessId = $ParentPid" -ErrorAction SilentlyContinue
        }
        foreach ($child in $children) {
            Stop-ProcessTree -ParentPid $child.ProcessId
        }
    } catch {
        # Silently continue on errors
    }

    # Stop the parent process itself
    Stop-Process -Id $ParentPid -Force -ErrorAction SilentlyContinue
}

# Helper function to run native commands and check exit codes immediately
function Run-Command {
    param(
        [Parameter(Mandatory=$true)]
        [ScriptBlock]$Script,
        [string]$WorkingDirectory = $null
    )
    $origDir = Get-Location
    try {
        if ($WorkingDirectory) {
            Set-Location $WorkingDirectory
        }
        # Execute the script block
        & $Script
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE"
        }
    } finally {
        Set-Location $origDir
    }
}

$backendProcess = $null
$frontendProcess = $null
$success = $true

# Define temporary files in workspace for hidden log output
$backendLog = Join-Path $InitialDirectory "backend_stdout.log"
$backendErr = Join-Path $InitialDirectory "backend_stderr.log"
$frontendLog = Join-Path $InitialDirectory "frontend_stdout.log"
$frontendErr = Join-Path $InitialDirectory "frontend_stderr.log"

try {
    # 1. Install Backend Dependencies
    Write-Host "`n[STEP 1] Installing Backend Dependencies..." -ForegroundColor Yellow
    Run-Command { python -m pip install --quiet -r backend/requirements.txt }

    # 2. Run Backend Unit/Integration Tests and Collect Coverage
    Write-Host "`n[STEP 2] Running Backend Tests and Collecting Coverage..." -ForegroundColor Yellow
    Run-Command { python -m pytest backend/test_api.py --cov=backend --cov-report=xml:backend/coverage.xml }

    # 3. Install Frontend Dependencies
    Write-Host "`n[STEP 3] Installing Frontend Dependencies..." -ForegroundColor Yellow
    Run-Command { npm install --silent } -WorkingDirectory "frontend"

    # 4. Run Frontend Unit/Integration Tests and Collect Coverage
    Write-Host "`n[STEP 4] Running Frontend Tests..." -ForegroundColor Yellow
    Run-Command { npx vitest run --coverage } -WorkingDirectory "frontend"

    # 5. Build Frontend Production Assets
    Write-Host "`n[STEP 5] Building Frontend production bundle..." -ForegroundColor Yellow
    Run-Command { npm run build } -WorkingDirectory "frontend"

    # 6. Run E2E Tests (Requires starting servers in background)
    Write-Host "`n[STEP 6] Running Playwright End-to-End Tests..." -ForegroundColor Yellow

    # Ensure local SQLite DB files are clean
    Remove-Item -Path "backend\identity.db", "backend\commerce.db", "backend\reviews.db" -ErrorAction SilentlyContinue
    Remove-Item -Path "identity.db", "commerce.db", "reviews.db" -ErrorAction SilentlyContinue

    # Track started processes for clean termination in finally block
    $startedProcesses = @()

    # Start services on port 18401-18403, 18400, and frontend on 18500
    Write-Host "Starting Identity Service..." -ForegroundColor DarkGray
    $procIdentity = Start-Process python -ArgumentList "-m uvicorn app.identity:app --host 127.0.0.1 --port 18401" -PassThru -NoNewWindow -WorkingDirectory "backend"
    $startedProcesses += $procIdentity

    Write-Host "Starting Commerce Service..." -ForegroundColor DarkGray
    $procCommerce = Start-Process python -ArgumentList "-m uvicorn app.commerce:app --host 127.0.0.1 --port 18402" -PassThru -NoNewWindow -WorkingDirectory "backend"
    $startedProcesses += $procCommerce

    Write-Host "Starting Reviews Service..." -ForegroundColor DarkGray
    $procReviews = Start-Process python -ArgumentList "-m uvicorn app.reviews:app --host 127.0.0.1 --port 18403" -PassThru -NoNewWindow -WorkingDirectory "backend"
    $startedProcesses += $procReviews

    Write-Host "Starting Gateway Service..." -ForegroundColor DarkGray
    $procGateway = Start-Process python -ArgumentList "-m uvicorn app.gateway:app --host 127.0.0.1 --port 18400" -PassThru -NoNewWindow -WorkingDirectory "backend"
    $startedProcesses += $procGateway

    Write-Host "Starting Frontend Service..." -ForegroundColor DarkGray
    $procFrontend = Start-Process npm.cmd -ArgumentList "run dev -- --port 18500 --strictPort --host 127.0.0.1" -PassThru -NoNewWindow -WorkingDirectory "frontend"
    $startedProcesses += $procFrontend

    # Wait for all services readiness
    Write-Host "Waiting for microservices to become ready..." -ForegroundColor DarkGray
    $ports = @(18401, 18402, 18403, 18400, 18500)
    foreach ($port in $ports) {
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            try {
                $conn = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
                $conn.Close()
                $ready = $true
                break
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        if (-not $ready) {
            throw "Microservice port $port failed to start or become ready in time."
        }
        Write-Host "Port $port is active!" -ForegroundColor Green
    }

    # Run Playwright E2E tests
    Write-Host "Triggering Playwright tests..." -ForegroundColor DarkGray
    Run-Command { npx playwright test } -WorkingDirectory "frontend"
    
    Write-Host "`nE2E Tests Completed Successfully!" -ForegroundColor Green

} catch {
    Write-Host "`n[ERROR] CI Pipeline Failed: $_" -ForegroundColor Red
    $success = $false
} finally {
    # Ensure cleanup of started processes
    Write-Host "`nCleaning up background server processes..." -ForegroundColor Yellow
    if ($startedProcesses) {
        foreach ($proc in $startedProcesses) {
            if ($proc -ne $null) {
                Write-Host "Terminating process tree for PID $($proc.Id)..." -ForegroundColor DarkGray
                Stop-ProcessTree -ParentPid $proc.Id
            }
        }
    }

    # Fallback cleanup on ports to ensure nothing is left listening
    $portsToKill = @(18400, 18401, 18402, 18403, 18500)
    foreach ($port in $portsToKill) {
        try {
            $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
            if ($conns) {
                foreach ($c in $conns) {
                    if ($c.OwningProcess -ne 0) {
                        Write-Host "Killing leftover process on port $port (PID $($c.OwningProcess))..." -ForegroundColor Red
                        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        } catch {
            # silently continue
        }
    }

    # Restore the original working directory
    if ($InitialDirectory) {
        Write-Host "Restoring original directory: $InitialDirectory" -ForegroundColor DarkGray
        Set-Location $InitialDirectory
    }
}

if (-not $success) {
    exit 1
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "       CI PIPELINE RUN COMPLETE & SUCCESSFUL      " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
