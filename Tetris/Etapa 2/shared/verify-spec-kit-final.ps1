param()

# Researcher verification only. Does not install dependencies or edit application/tests.
$ErrorActionPreference = 'Stop'
$stageRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Split-Path -Parent $stageRoot
$toolRoot = Join-Path $stageRoot 'Spec Kit'
$docs = Join-Path $toolRoot 'docs'
$python = @(
    (Join-Path $toolRoot 'backend\.venv\Scripts\python.exe'),
    (Join-Path $toolRoot '.venv\Scripts\python.exe'),
    (Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\python.exe')
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$records = [Collections.Generic.List[object]]::new()

function Invoke-RecordedCommand {
    param([string]$Name,[string]$Program,[string[]]$Arguments,[string]$Directory,[string]$Log)
    $started = [DateTime]::UtcNow
    Push-Location -LiteralPath $Directory
    try {
        & $Program @Arguments 1> $Log 2>&1
        $exitCode = $LASTEXITCODE
    } finally { Pop-Location }
    $records.Add([ordered]@{
        name=$Name; executable=$Program; arguments=$Arguments; directory=$Directory
        started_at_utc=$started.ToString('o'); ended_at_utc=[DateTime]::UtcNow.ToString('o')
        exit_code=$exitCode; log=$Log
    })
    $records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $docs 'verification-commands.json') -Encoding utf8
    Write-Output "$Name exit=$exitCode; log=$Log"
}

Invoke-RecordedCommand -Name 'backend-tests-and-coverage' -Program $python -Arguments @('-m','pytest','-q','--cov=app','--cov-report=term-missing',"--cov-report=xml:$docs\coverage.xml") -Directory (Join-Path $toolRoot 'backend') -Log (Join-Path $docs 'backend-coverage.log')
Invoke-RecordedCommand -Name 'frontend-tests-and-coverage' -Program $npm -Arguments @('run','test','--','--coverage') -Directory (Join-Path $toolRoot 'frontend') -Log (Join-Path $docs 'frontend-test-coverage.log')
Invoke-RecordedCommand -Name 'frontend-production-build' -Program $npm -Arguments @('run','build') -Directory (Join-Path $toolRoot 'frontend') -Log (Join-Path $docs 'frontend-build.log')
Invoke-RecordedCommand -Name 'frontend-dependency-audit' -Program $npm -Arguments @('audit','--json') -Directory (Join-Path $toolRoot 'frontend') -Log (Join-Path $docs 'npm-audit.json')

$missing = @('docs\coverage.xml','frontend\coverage\lcov.info') | Where-Object { -not (Test-Path -LiteralPath (Join-Path $toolRoot $_)) }
if ($missing.Count -gt 0) { throw "Missing current coverage outputs: $($missing -join ', ')" }
if (@($records | Where-Object { $_.exit_code -ne 0 }).Count -gt 0) { throw 'One or more verification commands failed; inspect the retained logs.' }
