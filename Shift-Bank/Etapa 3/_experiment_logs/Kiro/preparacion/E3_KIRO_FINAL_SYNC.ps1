[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('STAGE2-CLOSED')]
    [string]$ResearcherApproval
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($ResearcherApproval -cne 'STAGE2-CLOSED') {
    throw 'Final sync requires explicit researcher approval: -ResearcherApproval STAGE2-CLOSED'
}

$prepDir = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$evidenceDir = Split-Path -Parent $prepDir
$stage3Dir = Split-Path -Parent $evidenceDir
$projectDir = Split-Path -Parent $stage3Dir
$sourceDir = Join-Path $projectDir 'Etapa 2\Kiro'
$destDir = Join-Path $stage3Dir 'Kiro'
$provisionalManifest = Join-Path $prepDir 'E3_KIRO_PROVISIONAL_SHA256.csv'
$excludedDirectories = @(
    '.venv', 'venv', 'node_modules', 'dist', 'build', '__pycache__',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', '.scannerwork', '.sonar',
    '.cache', '.git', 'coverage', 'logs', 'sessions', 'session-logs',
    '_experiment_logs', 'sonarqube'
)

if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) {
    throw "Stage 2 source is missing: $sourceDir"
}
if (-not (Test-Path -LiteralPath $destDir -PathType Container)) {
    throw "Provisional Stage 3 copy is missing: $destDir"
}
if (-not (Test-Path -LiteralPath $provisionalManifest -PathType Leaf)) {
    throw "Provisional manifest is missing: $provisionalManifest"
}
if ((Get-Item -LiteralPath $destDir).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Stage 3 destination is a reparse point; refusing synchronization.'
}

function Get-EligibleFiles([string]$root) {
    $queue = [Collections.Generic.Queue[string]]::new()
    $queue.Enqueue($root)
    $result = [Collections.Generic.List[IO.FileInfo]]::new()
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        foreach ($item in Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Reparse point found in project tree: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                if ($excludedDirectories -notcontains $item.Name) {
                    $queue.Enqueue($item.FullName)
                }
                continue
            }
            if ($item.Length -ge 100MB) { continue }
            if ($item.Name -match '(^\.env($|\.)|\.(pyc|pyo|pem|key|p12|pfx)$|\.(db|sqlite|sqlite3)(-(wal|shm|journal))?$|-(wal|shm|journal)$|(^|[-_.])(token|credential|secret)([-_.]|$))') {
                continue
            }
            $result.Add($item)
        }
    }
    return $result
}

function Get-HashMap([string]$root) {
    $map = @{}
    foreach ($file in Get-EligibleFiles $root) {
        $relative = $file.FullName.Substring($root.Length + 1).Replace('\', '/')
        $map[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return $map
}

function Assert-MapsEqual($expected, $actual, [string]$label) {
    $differences = [Collections.Generic.List[string]]::new()
    foreach ($path in $expected.Keys) {
        if (-not $actual.ContainsKey($path)) {
            $differences.Add("missing: $path")
        } elseif ($actual[$path] -cne $expected[$path]) {
            $differences.Add("changed: $path")
        }
    }
    foreach ($path in $actual.Keys) {
        if (-not $expected.ContainsKey($path)) { $differences.Add("unexpected: $path") }
    }
    if ($differences.Count -gt 0) {
        throw "$label differs from its approved snapshot:`n$($differences -join "`n")`nNo synchronization was performed."
    }
}

# Refuse to replace Stage 3 if a file was edited, removed, or added since preparation.
$provisionalRows = Import-Csv -LiteralPath $provisionalManifest
$provisionalMap = @{}
foreach ($row in $provisionalRows) { $provisionalMap[$row.relative_path] = $row.sha256 }
$currentStage3Map = Get-HashMap $destDir
Assert-MapsEqual $provisionalMap $currentStage3Map 'Provisional Stage 3 tree'

$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$stagingDir = Join-Path $stage3Dir ".E3_KIRO_FINALIZING_$stamp"
$backupDir = Join-Path $stage3Dir "Kiro.provisional-backup_$stamp"
$manifestName = "E3_KIRO_FINAL_SHA256_$stamp.csv"
$reportName = "E3_KIRO_FINALIZED_$stamp.md"
$manifestPath = Join-Path $prepDir $manifestName
$reportPath = Join-Path $prepDir $reportName
if (Test-Path -LiteralPath $stagingDir) { throw "Staging path already exists: $stagingDir" }
if (Test-Path -LiteralPath $backupDir) { throw "Backup path already exists: $backupDir" }
if ((Test-Path -LiteralPath $manifestPath) -or (Test-Path -LiteralPath $reportPath)) {
    throw 'Final evidence path already exists; no evidence file was overwritten.'
}

$gitHead = (& git -C $projectDir rev-parse HEAD 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not read repository HEAD: $gitHead" }
$gitStatus = (& git -C $projectDir status --short -- 'Shift-Bank/Etapa 2/Kiro' 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not read Stage 2 working-tree status: $gitStatus" }

$sourceBefore = Get-HashMap $sourceDir
New-Item -ItemType Directory -Path $stagingDir | Out-Null
try {
    foreach ($file in Get-EligibleFiles $sourceDir) {
        $relative = $file.FullName.Substring($sourceDir.Length + 1)
        $target = Join-Path $stagingDir $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
    }
    $stagedMap = Get-HashMap $stagingDir
    Assert-MapsEqual $sourceBefore $stagedMap 'Copied Stage 2 snapshot'
    $sourceAfter = Get-HashMap $sourceDir
    Assert-MapsEqual $sourceBefore $sourceAfter 'Stage 2 source during copy'
    $stage3BeforeSwap = Get-HashMap $destDir
    Assert-MapsEqual $provisionalMap $stage3BeforeSwap 'Provisional Stage 3 tree before swap'

    # Keep the old provisional tree as a sibling backup; never delete experimental work.
    Move-Item -LiteralPath $destDir -Destination $backupDir
    try {
        Move-Item -LiteralPath $stagingDir -Destination $destDir
    } catch {
        Move-Item -LiteralPath $backupDir -Destination $destDir
        throw
    }
} catch {
    if (Test-Path -LiteralPath $stagingDir) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
    throw
}

$finalMap = Get-HashMap $destDir
Assert-MapsEqual $sourceBefore $finalMap 'Final Stage 3 tree'

$rows = foreach ($relative in ($finalMap.Keys | Sort-Object)) {
    $filePath = Join-Path $destDir $relative.Replace('/', '\')
    [pscustomobject]@{
        relative_path = $relative
        size_bytes = (Get-Item -LiteralPath $filePath).Length
        sha256 = $finalMap[$relative]
    }
}
$rows | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8
$sourceStatus = if ([string]::IsNullOrWhiteSpace($gitStatus)) { '(clean)' } else { $gitStatus }
$report = @"
# Shift Bank E3 Kiro — finalized Stage 2 baseline

Status: FINALIZED after explicit researcher approval (`STAGE2-CLOSED`).
Synchronization time (UTC): $([DateTime]::UtcNow.ToString('o'))
Source: $sourceDir
Destination: $destDir
Git HEAD at synchronization: $gitHead
Stage 2 working-tree status: $sourceStatus
Copied files: $($rows.Count)
SHA-256 manifest: $manifestName
Preserved provisional backup: $backupDir

The copy was staged, hash-verified against the source before/after transfer, and swapped only after confirming Stage 3 still matched its provisional manifest. No historical databases, runtime secrets, experimental evidence, or excluded build/cache artifacts were copied.
"@
Set-Content -LiteralPath $reportPath -Value $report -Encoding utf8
Write-Output "Finalized baseline: $destDir"
Write-Output "Manifest: $manifestPath"
Write-Output "Report: $reportPath"
Write-Output "Preserved provisional backup: $backupDir"
