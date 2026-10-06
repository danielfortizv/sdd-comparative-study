param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $root 'Bmad Method Full'
$docs = Join-Path $toolRoot 'docs'
$scanner = Join-Path $root '_toolchain\venv\Scripts\pysonar.exe'
$tokenPath = Join-Path $root '_toolchain\sonar-token.txt'
$projectKey = 'tetris-stage1-bmad-full'

if (-not (Test-Path -LiteralPath (Join-Path $toolRoot 'backend\app\core'))) { throw 'Missing backend/app/core source.' }
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot 'backend\app\tests'))) { throw 'Missing backend/app/tests.' }
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot 'frontend\src'))) { throw 'Missing frontend/src source.' }
if (-not (Test-Path -LiteralPath (Join-Path $docs 'coverage.xml'))) { throw 'Missing docs/coverage.xml.' }
if (-not (Test-Path -LiteralPath $tokenPath)) { throw 'Missing private Sonar token.' }

$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
$env:SONAR_USER_HOME = Join-Path $toolRoot '.sonar-user-home'
Push-Location -LiteralPath $toolRoot
try {
    & $scanner `
        --token $token `
        --sonar-project-key $projectKey `
        --sonar-project-name 'Tetris Stage 1 BMAD Full' `
        --sonar-host-url 'http://127.0.0.1:9000' `
        --sonar-sources 'backend/app/core,backend/app/main.py,frontend/src' `
        --sonar-tests 'backend/app/tests' `
        --sonar-python-coverage-report-paths 'docs/coverage.xml' `
        1> (Join-Path $docs 'sonar-scan.log') 2>&1
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Variable token
}
Write-Output "Scanner exit code: $code; log: $docs\sonar-scan.log"
exit $code
