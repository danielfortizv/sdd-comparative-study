# Stop-Stage4.ps1
# Teardown Stage 4 microservices stack
Write-Host "Stopping Stage 4 microservices stack..."

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(".")
}

$PidsFile = Join-Path $ScriptDir "stage4-pids.json"

if (Test-Path $PidsFile) {
    $Pids = Get-Content -Raw -Path $PidsFile | ConvertFrom-Json
    foreach ($ProcName in $Pids.psobject.Properties.Name) {
        $PidVal = $Pids.$ProcName
        if ($PidVal) {
            Write-Host "Stopping $ProcName (PID: $PidVal)..."
            # Verify PID ownership / existence using ([int]$PidVal) casting syntax
            $Proc = Get-Process -Id ([int]$PidVal) -ErrorAction SilentlyContinue
            if ($Proc) {
                Stop-Process -Id ([int]$PidVal) -Force -ErrorAction SilentlyContinue
            } else {
                Write-Host "$ProcName with PID $PidVal was not running."
            }
        }
    }
    Remove-Item $PidsFile -ErrorAction SilentlyContinue
} else {
    Write-Host "No stage4-pids.json file found. Cleaning up processes on Stage 4 ports..."
}

# Fallback/insurance check: always clean ports 18000, 18001, 18002, 18003, 18100
$Ports = @(18000, 18001, 18002, 18003, 18100)
$AllowedProcessNames = @("python", "node", "cmd", "npm")

foreach ($Port in $Ports) {
    $Netstat = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
    if ($Netstat) {
        foreach ($Line in $Netstat) {
            $NetstatLine = $Line.ToString()
            $Tokens = $NetstatLine -split '\s+' | Where-Object { $_ }
            $PidVal = $Tokens[-1]
            if ($PidVal -as [int]) {
                $IntPid = [int]$PidVal
                $Proc = Get-Process -Id ([int]$IntPid) -ErrorAction SilentlyContinue
                if ($Proc) {
                    if ($AllowedProcessNames -contains $Proc.ProcessName.ToLower()) {
                        Write-Host "Killing residual owned process listening on port $Port (Name: $($Proc.ProcessName), PID: $IntPid)..."
                        Stop-Process -Id ([int]$IntPid) -Force -ErrorAction SilentlyContinue
                    } else {
                        Write-Host "Skipping non-owned process listening on port $Port (Name: $($Proc.ProcessName), PID: $IntPid) to protect system integrity."
                    }
                }
            }
        }
    }
}

Write-Host "Teardown complete."
