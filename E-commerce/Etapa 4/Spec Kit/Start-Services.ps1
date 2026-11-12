# Start-Services.ps1
# Starts all four Stage 4 Python services, and optionally the React frontend, natively in the background.

param(
    [switch]$Frontend
)

$ErrorActionPreference = "Stop"

# Establish stable absolute paths
$rootPath = Resolve-Path $PSScriptRoot
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"
$logDir = Join-Path $rootPath ".logs"
$pidsFile = Join-Path $rootPath ".services.pids"

# 1. Clean partial starts of owned processes first
Write-Host "Cleaning any partial starts or previously running services..." -ForegroundColor Yellow
if (Test-Path (Join-Path $rootPath "Stop-Services.ps1")) {
    & (Join-Path $rootPath "Stop-Services.ps1") | Out-Null
}

# 2. Ensure log directory exists
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

$JWT_SECRET = "stage4-super-secret-key-12345678"
$AMQP_URL = "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_speckit"
$EVENT_NAMESPACE = "stage4.speckit"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Starting Stage 4 Microservices       " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if RabbitMQ is running on port 5672
Write-Host "Checking local RabbitMQ broker availability on port 5672..." -ForegroundColor Yellow
$tcpConnection = New-Object System.Net.Sockets.TcpClient
$asyncResult = $tcpConnection.BeginConnect("127.0.0.1", 5672, $null, $null)
$wait = $asyncResult.AsyncWaitHandle.WaitOne(2000, $true)

if (-not $wait) {
    Write-Host "ERROR: RabbitMQ is not reachable on 127.0.0.1:5672." -ForegroundColor Red
    Write-Host "Please ensure that your local WSL or Windows RabbitMQ instance is active." -ForegroundColor Red
    exit 1
} else {
    $tcpConnection.EndConnect($asyncResult)
    $tcpConnection.Close()
    Write-Host "RabbitMQ broker is ONLINE." -ForegroundColor Green
}

# Configure stable database environment variables pointing to absolute paths (data survives restarts!)
$env:IDENTITY_DB_PATH = Join-Path $backendPath "identity.db"
$env:COMMERCE_DB_PATH = Join-Path $backendPath "commerce.db"
$env:REVIEWS_DB_PATH = Join-Path $backendPath "reviews.db"

$env:JWT_SECRET = $JWT_SECRET
$env:AMQP_URL = $AMQP_URL
$env:EVENT_NAMESPACE = $EVENT_NAMESPACE
$env:IDENTITY_SERVICE_URL = "http://127.0.0.1:18601"
$env:COMMERCE_SERVICE_URL = "http://127.0.0.1:18602"
$env:REVIEWS_SERVICE_URL = "http://127.0.0.1:18603"
$env:RUN_WORKERS = "true"

# Helper to launch and record a service
function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$AppModule,
        [int]$Port,
        [string]$LogName
    )
    Write-Host "Launching $Name Service on port $Port..." -ForegroundColor Yellow
    
    $outFile = Join-Path $logDir "$LogName.log"
    $errFile = Join-Path $logDir "$LogName.err"
    
    $proc = Start-Process python -ArgumentList "-m uvicorn $AppModule --port $Port" `
        -WorkingDirectory $backendPath `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile
        
    # Record owned PID immediately
    "$($proc.Id),python" | Out-File -FilePath $pidsFile -Append -Encoding utf8
    return $proc.Id
}

# Start background services
$pid_identity = Start-ServiceProcess "Identity" "src.services.identity.main:app" 18601 "identity"
$pid_commerce = Start-ServiceProcess "Commerce" "src.services.commerce.main:app" 18602 "commerce"
$pid_reviews = Start-ServiceProcess "Reviews" "src.services.reviews.main:app" 18603 "reviews"
$pid_gateway = Start-ServiceProcess "API Gateway" "src.services.gateway.main:app" 18600 "gateway"

# Start Frontend if requested
if ($Frontend) {
    Write-Host "Launching React Frontend on port 18700..." -ForegroundColor Yellow
    $env:PORT = "18700"
    $env:HOST = "127.0.0.1"
    $env:BROWSER = "none"
    $env:REACT_APP_API_URL = "http://127.0.0.1:18600"
    
    $outFile = Join-Path $logDir "frontend.log"
    $errFile = Join-Path $logDir "frontend.err"
    
    $proc = Start-Process "npm.cmd" -ArgumentList "start" `
        -WorkingDirectory $frontendPath `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile
        
    # Record owned PID immediately (npm is started, which might spawn node child processes)
    "$($proc.Id),npm" | Out-File -FilePath $pidsFile -Append -Encoding utf8
}

# Perform Health Checks with readiness loops
Write-Host "Waiting for services to become healthy..." -ForegroundColor Yellow
$healthy = $false
$attempts = 0
$maxAttempts = 15

while (-not $healthy -and $attempts -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $attempts++
    
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:18600/api/products" -Method Get -TimeoutSec 2
        if ($resp) {
            $healthy = $true
        }
    } catch {
        # Keep waiting
    }
}

$frontendReady = $false
if ($Frontend) {
    Write-Host "Waiting for Frontend to become ready on port 18700..." -ForegroundColor Yellow
    $feAttempts = 0
    $feMaxAttempts = 30
    
    while (-not $frontendReady -and $feAttempts -lt $feMaxAttempts) {
        Start-Sleep -Seconds 1
        $feAttempts++
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect("127.0.0.1", 18700, $null, $null)
            $wait = $async.AsyncWaitHandle.WaitOne(500, $true)
            if ($wait) {
                $tcp.EndConnect($async)
                $frontendReady = $true
            }
            $tcp.Close()
        } catch {
            # continue waiting
        }
    }
}

if ($healthy -and (-not $Frontend -or $frontendReady)) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host " SUCCESS: All services are healthy and running!" -ForegroundColor Green
    Write-Host " Gateway:   http://localhost:18600" -ForegroundColor Green
    Write-Host " Identity:  http://localhost:18601" -ForegroundColor Green
    Write-Host " Commerce:  http://localhost:18602" -ForegroundColor Green
    Write-Host " Reviews:   http://localhost:18603" -ForegroundColor Green
    if ($Frontend) {
        Write-Host " Frontend:  http://localhost:18700" -ForegroundColor Green
    }
    Write-Host " Logs folder: $logDir" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "WARNING: Services took too long to respond. Please check the logs in $logDir or run Stop-Services.ps1." -ForegroundColor Red
}
