# Start-Services.ps1
# PowerShell script to launch and verify all Stage 4 microservices locally

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Starting E-Commerce Microservices (Stage 4)..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Create logs directory for hidden/logged processes
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Define stable absolute database paths for the normal startup
$env:IDENTITY_DB_FILE = Resolve-Path "backend\identity.db" -ErrorAction SilentlyContinue
if (-not $env:IDENTITY_DB_FILE) {
    $env:IDENTITY_DB_FILE = [System.IO.Path]::GetFullPath("backend\identity.db")
}
$env:COMMERCE_DB_FILE = Resolve-Path "backend\commerce.db" -ErrorAction SilentlyContinue
if (-not $env:COMMERCE_DB_FILE) {
    $env:COMMERCE_DB_FILE = [System.IO.Path]::GetFullPath("backend\commerce.db")
}
$env:REVIEWS_DB_FILE = Resolve-Path "backend\reviews.db" -ErrorAction SilentlyContinue
if (-not $env:REVIEWS_DB_FILE) {
    $env:REVIEWS_DB_FILE = [System.IO.Path]::GetFullPath("backend\reviews.db")
}

# 1. Start Identity Service (Port 18401)
$identityProc = Start-Process -FilePath "uvicorn" -ArgumentList "app.identity:app --port 18401 --host 127.0.0.1" -WorkingDirectory "backend" -PassThru -NoNewWindow -RedirectStandardOutput "logs\identity.out.log" -RedirectStandardError "logs\identity.err.log"
$identityPid = $identityProc.Id
Write-Host "Launched Identity Service (PID: $identityPid)" -ForegroundColor Yellow

# 2. Start Commerce Service (Port 18402)
$commerceProc = Start-Process -FilePath "uvicorn" -ArgumentList "app.commerce:app --port 18402 --host 127.0.0.1" -WorkingDirectory "backend" -PassThru -NoNewWindow -RedirectStandardOutput "logs\commerce.out.log" -RedirectStandardError "logs\commerce.err.log"
$commercePid = $commerceProc.Id
Write-Host "Launched Commerce Service (PID: $commercePid)" -ForegroundColor Yellow

# 3. Start Reviews Service (Port 18403)
$reviewsProc = Start-Process -FilePath "uvicorn" -ArgumentList "app.reviews:app --port 18403 --host 127.0.0.1" -WorkingDirectory "backend" -PassThru -NoNewWindow -RedirectStandardOutput "logs\reviews.out.log" -RedirectStandardError "logs\reviews.err.log"
$reviewsPid = $reviewsProc.Id
Write-Host "Launched Reviews Service (PID: $reviewsPid)" -ForegroundColor Yellow

# 4. Start Gateway Service (Port 18400)
$gatewayProc = Start-Process -FilePath "uvicorn" -ArgumentList "app.gateway:app --port 18400 --host 127.0.0.1" -WorkingDirectory "backend" -PassThru -NoNewWindow -RedirectStandardOutput "logs\gateway.out.log" -RedirectStandardError "logs\gateway.err.log"
$gatewayPid = $gatewayProc.Id
Write-Host "Launched Gateway Service (PID: $gatewayPid)" -ForegroundColor Yellow

# 5. Start Frontend Service via Node + local Vite directly (Port 18500)
$frontendProc = Start-Process -FilePath "node" -ArgumentList "node_modules/vite/bin/vite.js --port 18500 --strictPort --host 127.0.0.1" -WorkingDirectory "frontend" -PassThru -NoNewWindow -RedirectStandardOutput "logs\frontend.out.log" -RedirectStandardError "logs\frontend.err.log"
$frontendPid = $frontendProc.Id
Write-Host "Launched Frontend Service (PID: $frontendPid)" -ForegroundColor Yellow

# Save PIDs to services-pids.json for clean stop management
$pids = @{
    identity = $identityPid
    commerce = $commercePid
    reviews = $reviewsPid
    gateway = $gatewayPid
    frontend = $frontendPid
} | ConvertTo-Json

$pids | Out-File -FilePath "services-pids.json" -Encoding utf8

# Deterministic Readiness Checks
Write-Host "Running readiness port checks..." -ForegroundColor Cyan
$ports = @(18401, 18402, 18403, 18400, 18500)
$allReady = $true

foreach ($port in $ports) {
    $ready = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $conn = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
            $conn.Close()
            $ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($ready) {
        Write-Host "Port $port is active and listening." -ForegroundColor Green
    } else {
        Write-Host "Port $port failed to start within timeout limit." -ForegroundColor Red
        $allReady = $false
    }
}

if ($allReady) {
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "All Stage 4 microservices launched successfully!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
} else {
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "Warning: Some microservices failed to respond." -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
}
