# Stop-Services.ps1
# PowerShell script to cleanly stop all Stage 4 microservices

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Stopping E-Commerce Microservices (Stage 4)..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Helper function to recursively stop a parent process and all its children
function Stop-ProcessTree {
    param(
        [Parameter(Mandatory=$true)]
        [int]$ParentPid
    )
    try {
        # Query children using Get-CimInstance or Get-WmiObject
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentPid" -ErrorAction SilentlyContinue
        if ($null -eq $children) {
            $children = Get-WmiObject Win32_Process -Filter "ParentProcessId = $ParentPid" -ErrorAction SilentlyContinue
        }
        if ($children) {
            foreach ($child in $children) {
                Stop-ProcessTree -ParentPid $child.ProcessId
            }
        }
    } catch {
        # ignore errors
    }

    # Stop the process itself
    Stop-Process -Id $ParentPid -Force -ErrorAction SilentlyContinue
}

if (Test-Path "services-pids.json") {
    $pids = Get-Content -Raw "services-pids.json" | ConvertFrom-Json
    foreach ($name in $pids.PSObject.Properties.Name) {
        $pidVal = $pids.$name
        if ($pidVal) {
            Write-Host "Stopping service $name and its owned process tree (PID: $pidVal)..." -ForegroundColor Yellow
            Stop-ProcessTree -ParentPid $pidVal
            Write-Host "Service $name stopped." -ForegroundColor Green
        }
    }
    Remove-Item "services-pids.json" -ErrorAction SilentlyContinue
} else {
    Write-Host "services-pids.json not found. No processes to cleanly shut down." -ForegroundColor Yellow
}

Write-Host "================================================" -ForegroundColor Green
Write-Host "All Stage 4 microservices stopped successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
