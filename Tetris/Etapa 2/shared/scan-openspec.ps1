param()

$ErrorActionPreference = 'Stop'
$stageRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Split-Path -Parent $stageRoot
$toolRoot = Join-Path $stageRoot 'OpenSpec'
$docs = Join-Path $toolRoot 'docs'
$scanner = Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\pysonar.exe'
$tokenPath = Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt'
$key = 'tetris-stage2-openspec'

foreach ($p in @($scanner,$tokenPath,(Join-Path $docs 'coverage.xml'))) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing scan input: $p" }
}
$frontendLcov = Join-Path $toolRoot 'frontend\coverage\lcov.info'
if (-not (Test-Path -LiteralPath $frontendLcov)) { throw "Missing scan input: $frontendLcov" }
$sourceFiles = @('backend/engine.py','backend/main.py','backend/models.py','frontend/src')
$testFiles = @(Get-ChildItem -LiteralPath (Join-Path $toolRoot 'backend') -Filter 'test*.py' -File | ForEach-Object { 'backend/' + $_.Name })
if (-not $testFiles) { throw 'No backend test files found.' }
$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
$env:SONAR_USER_HOME = Join-Path $toolRoot '.sonar-user-home'
Push-Location -LiteralPath $toolRoot
try {
    & $scanner `
        --token $token `
        --sonar-project-key $key `
        --sonar-project-name 'Tetris Stage 2 OpenSpec' `
        --sonar-host-url 'http://127.0.0.1:9000' `
        --sonar-sources ($sourceFiles -join ',') `
        --sonar-tests ($testFiles -join ',') `
        '-Dsonar.exclusions=frontend/src/**/*.test.ts,frontend/src/**/*.test.tsx' `
        --sonar-python-coverage-report-paths 'docs/coverage.xml' `
        '-Dsonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info' `
        1> (Join-Path $docs 'sonar-scan.log') 2>&1
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Variable token
}
Write-Output "Scanner exit code: $code; project: $key; log: $docs\sonar-scan.log"
exit $code
