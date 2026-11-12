# Stop-Services.ps1
# Gracefully and forcefully terminates all natively running Stage 4 background processes.

Write-Host "Stopping all running microservice processes..." -ForegroundColor Yellow

$rootPath = Resolve-Path $PSScriptRoot
$pidsFile = Join-Path $rootPath ".services.pids"

if (Test-Path $pidsFile) {
    $entries = Get-Content $pidsFile
    foreach ($entry in $entries) {
        $entry = $entry.Trim()
        if ($entry -and $entry -match "^\d+,\w+") {
            $parts = $entry.Split(",")
            $pid_val = [int]$parts[0]
            $proc_name = $parts[1]
            try {
                $process = Get-Process -Id $pid_val -ErrorAction SilentlyContinue
                if ($process -and ($process.ProcessName -match "python" -or $process.ProcessName -match "node" -or $process.ProcessName -match "npm")) {
                    Write-Host "Killing owned process $pid_val ($($process.ProcessName))..." -ForegroundColor Cyan
                    Stop-Process -Id $pid_val -Force
                }
            } catch {
                Write-Host "Failed to stop process ${pid_val}: $($_)" -ForegroundColor Red
            }
        }
    }
    Remove-Item $pidsFile -Force -ErrorAction SilentlyContinue
    Write-Host "All registered background service processes stopped." -ForegroundColor Green
} else {
    Write-Host "No active service PID file found. Checking for orphaned processes on our ports..." -ForegroundColor Yellow
}

# Fallback port-based cleanup of any uvicorn/node endpoints on our ports (guarding non-owned processes)
$ports = @(18600, 18601, 18602, 18603, 18700)
foreach ($port in $ports) {
    try {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $procId = $conn.OwningProcess
            if ($procId) {
                $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($process -and ($process.ProcessName -match "python" -or $process.ProcessName -match "node" -or $process.ProcessName -match "npm")) {
                    Write-Host "Cleaning up orphaned process $procId ($($process.ProcessName)) listening on port $port..." -ForegroundColor Cyan
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } catch {
        # Silent pass
    }
}

Write-Host "Done cleanup." -ForegroundColor Green
