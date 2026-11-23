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

    # Clean up old log files
    Remove-Item $backendLog -ErrorAction SilentlyContinue
    Remove-Item $backendErr -ErrorAction SilentlyContinue
    Remove-Item $frontendLog -ErrorAction SilentlyContinue
    Remove-Item $frontendErr -ErrorAction SilentlyContinue

    # Start backend in background
    Write-Host "Starting Backend server..." -ForegroundColor DarkGray
    $backendProcess = Start-Process python -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow -WorkingDirectory "backend" -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr
    
    # Start frontend in background (using npm run dev to serve on 3000)
    Write-Host "Starting Frontend server..." -ForegroundColor DarkGray
    $frontendProcess = Start-Process npm.cmd -ArgumentList "run dev" -PassThru -NoNewWindow -WorkingDirectory "frontend" -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

    # Wait for backend readiness
    Write-Host "Waiting for Backend to become ready..." -ForegroundColor DarkGray
    $backendReady = $false
    for ($i = 0; $i -lt 15; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/products" -UseBasicParsing -TimeoutSec 1
            if ($resp.StatusCode -eq 200) {
                $backendReady = $true
                Write-Host "Backend is ready!" -ForegroundColor Green
                break
            }
        } catch {
            # Quietly wait
        }
        Start-Sleep -Seconds 1
    }

    if (-not $backendReady) {
        throw "Backend failed to start or become ready in time."
    }

    # Wait for frontend readiness
    Write-Host "Waiting for Frontend to become ready..." -ForegroundColor DarkGray
    $frontendReady = $false
    for ($i = 0; $i -lt 15; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 1
            if ($resp.StatusCode -eq 200) {
                $frontendReady = $true
                Write-Host "Frontend is ready!" -ForegroundColor Green
                break
            }
        } catch {
            # Quietly wait
        }
        Start-Sleep -Seconds 1
    }

    if (-not $frontendReady) {
        throw "Frontend failed to start or become ready in time."
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
    if ($backendProcess -ne $null) {
        Write-Host "Terminating backend process tree (PID $($backendProcess.Id))..." -ForegroundColor DarkGray
        Stop-ProcessTree -ParentPid $backendProcess.Id
    }
    if ($frontendProcess -ne $null) {
        Write-Host "Terminating frontend process tree (PID $($frontendProcess.Id))..." -ForegroundColor DarkGray
        Stop-ProcessTree -ParentPid $frontendProcess.Id
    }

    # Clean up temporary logs
    Remove-Item $backendLog -ErrorAction SilentlyContinue
    Remove-Item $backendErr -ErrorAction SilentlyContinue
    Remove-Item $frontendLog -ErrorAction SilentlyContinue
    Remove-Item $frontendErr -ErrorAction SilentlyContinue

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
