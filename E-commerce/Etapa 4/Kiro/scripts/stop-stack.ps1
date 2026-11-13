# Stop the Stage 4 stack started by start-stack.ps1 (owned-process cleanup).
#
# Reads .stage4-pids.json and stops exactly the processes this stack still owns.
# Each record carries the pid plus the process name and start time captured at
# launch; a process is only killed when a live process with that pid still has
# the same name and start time. This guards against a stale/reused PID (the OS
# having recycled the number for an unrelated process) so we never kill a
# bystander. It does NOT touch the RabbitMQ broker, managed independently in WSL.

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root ".stage4-pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "No .stage4-pids.json found; nothing to stop."
    return
}

$records = Get-Content $pidFile | ConvertFrom-Json
# A single-element JSON array deserializes to a scalar; normalize to an array.
if ($records -isnot [System.Array]) { $records = @($records) }

foreach ($record in $records) {
    # Backward/parse tolerance: a record may be a bare integer pid or an object.
    if ($record -is [int] -or $record -is [long]) {
        $recordPid = [int]$record
        $expectedName = $null
        $expectedStart = $null
        $label = ""
    } else {
        $recordPid = [int]$record.pid
        $expectedName = $record.processName
        # ConvertFrom-Json turns an ISO-8601 string into a [DateTime]; normalize
        # back to the same round-trip string we recorded at launch so the guard
        # compares like-for-like regardless of how the value deserialized.
        if ($null -ne $record.startTime) {
            if ($record.startTime -is [datetime]) {
                $expectedStart = $record.startTime.ToString("o")
            } else {
                $expectedStart = ([datetime]$record.startTime).ToString("o")
            }
        } else {
            $expectedStart = $null
        }
        $label = $record.name
    }

    $proc = Get-Process -Id $recordPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host "Process $recordPid ($label) is no longer running; skipping."
        continue
    }

    # Guard against a reused PID: identity must still match what we recorded.
    $identityMatches = $true
    if ($expectedName) {
        if ($proc.ProcessName -ne $expectedName) { $identityMatches = $false }
    }
    if ($identityMatches -and $expectedStart) {
        $actualStart = $proc.StartTime.ToString("o")
        if ($actualStart -ne $expectedStart) { $identityMatches = $false }
    }

    if (-not $identityMatches) {
        Write-Host "Process $recordPid no longer matches the owned $label (PID reused); skipping."
        continue
    }

    Write-Host "Stopping process $recordPid ($($proc.ProcessName), $label)..."
    # Kill the process tree so uvicorn reload/child workers also stop.
    taskkill /PID $recordPid /T /F | Out-Null
}

Remove-Item $pidFile -Force
Write-Host "Stage 4 stack stopped."
