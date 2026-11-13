# Start-Stage4.ps1
# Start RabbitMQ, 4 backend services, and frontend
Write-Host "Starting Stage 4 microservices stack..."

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(".")
}

$RuntimeFile = Join-Path $ScriptDir "stage4-runtime.json"
$Runtime = Get-Content -Raw -Path $RuntimeFile | ConvertFrom-Json
$env:AMQP_URL = $Runtime.amqp_url
$env:EVENT_NAMESPACE = $Runtime.event_namespace
$env:VITE_API_URL = "http://127.0.0.1:$($Runtime.gateway_port)"

$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$LogsDir = Join-Path $ScriptDir "logs"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Ensure any previous instance is stopped
if (Test-Path (Join-Path $ScriptDir "stage4-pids.json")) {
    Write-Host "Teardown previous processes..."
    & (Join-Path $ScriptDir "Stop-Stage4.ps1")
}

Write-Host "Starting Identity Service on port $($Runtime.identity_port)..."
$IdentityProc = Start-Process python -ArgumentList "app/identity/main.py" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogsDir "identity.log") `
    -RedirectStandardError (Join-Path $LogsDir "identity_err.log") `
    -PassThru

Write-Host "Starting Commerce Service on port $($Runtime.commerce_port)..."
$CommerceProc = Start-Process python -ArgumentList "app/commerce/main.py" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogsDir "commerce.log") `
    -RedirectStandardError (Join-Path $LogsDir "commerce_err.log") `
    -PassThru

Write-Host "Starting Reviews Service on port $($Runtime.reviews_port)..."
$ReviewsProc = Start-Process python -ArgumentList "app/reviews/main.py" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogsDir "reviews.log") `
    -RedirectStandardError (Join-Path $LogsDir "reviews_err.log") `
    -PassThru

# Give microservices a brief moment to bind to ports before starting gateway
Start-Sleep -Seconds 2

Write-Host "Starting API Gateway on port $($Runtime.gateway_port)..."
$GatewayProc = Start-Process python -ArgumentList "app/gateway/main.py" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogsDir "gateway.log") `
    -RedirectStandardError (Join-Path $LogsDir "gateway_err.log") `
    -PassThru

Write-Host "Starting Frontend on port $($Runtime.frontend_port)..."
$FrontendProc = Start-Process cmd -ArgumentList "/c npm run dev -- --port $($Runtime.frontend_port)" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogsDir "frontend.log") `
    -RedirectStandardError (Join-Path $LogsDir "frontend_err.log") `
    -PassThru

# Write PIDs to a file for clean teardown and verification
$Pids = [PSCustomObject]@{
    Identity = $IdentityProc.Id
    Commerce = $CommerceProc.Id
    Reviews  = $ReviewsProc.Id
    Gateway  = $GatewayProc.Id
    Frontend = $FrontendProc.Id
}
$Pids | ConvertTo-Json | Out-File -FilePath (Join-Path $ScriptDir "stage4-pids.json") -Force

# Wait for health check readiness
Write-Host "Waiting for services to become healthy..."
$Healthy = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $Res = Invoke-RestMethod -Uri "http://127.0.0.1:$($Runtime.gateway_port)/health" -TimeoutSec 1
        if ($Res.status -eq "healthy" -and $Res.services.identity.status -eq "healthy" -and $Res.services.commerce.status -eq "healthy" -and $Res.services.reviews.status -eq "healthy") {
            $Healthy = $true
            break
        }
    } catch {
        # ignore
    }
    Start-Sleep -Seconds 1
}

if ($Healthy) {
    Write-Host "All processes started successfully and verified healthy!"
    Write-Host "Access application at http://127.0.0.1:$($Runtime.frontend_port)"
} else {
    Write-Warning "Some services failed readiness check. Check logs at: $LogsDir"
    # Show last few lines of errors for debugging
    if (Test-Path (Join-Path $LogsDir "identity_err.log")) {
        Write-Host "--- Identity Err ---"
        Get-Content (Join-Path $LogsDir "identity_err.log") -Tail 5
    }
    if (Test-Path (Join-Path $LogsDir "commerce_err.log")) {
        Write-Host "--- Commerce Err ---"
        Get-Content (Join-Path $LogsDir "commerce_err.log") -Tail 5
    }
    if (Test-Path (Join-Path $LogsDir "reviews_err.log")) {
        Write-Host "--- Reviews Err ---"
        Get-Content (Join-Path $LogsDir "reviews_err.log") -Tail 5
    }
    if (Test-Path (Join-Path $LogsDir "gateway_err.log")) {
        Write-Host "--- Gateway Err ---"
        Get-Content (Join-Path $LogsDir "gateway_err.log") -Tail 5
    }
}
