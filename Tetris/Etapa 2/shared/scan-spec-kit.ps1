param()

$ErrorActionPreference = 'Stop'
$stageRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Split-Path -Parent $stageRoot
$toolRoot = Join-Path $stageRoot 'Spec Kit'
$docs = Join-Path $toolRoot 'docs'
$scanner = Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\pysonar.exe'
$tokenPath = Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt'
$key = 'tetris-stage2-speckit'
foreach ($p in @($scanner,$tokenPath,(Join-Path $docs 'coverage.xml'))) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing scan input: $p" }
}
$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
$env:SONAR_USER_HOME = Join-Path $toolRoot '.sonar-user-home'
$scanArgs = @(
    '--token', $token,
    '--sonar-project-key', $key,
    '--sonar-project-name', 'Tetris Stage 2 Spec Kit',
    '--sonar-host-url', 'http://127.0.0.1:9000',
    '--sonar-sources', 'backend/app,frontend/src',
    '--sonar-tests', 'backend/tests,frontend/tests',
    '--sonar-python-coverage-report-paths', 'docs/coverage.xml'
)
$lcov = Join-Path $toolRoot 'frontend\coverage\lcov.info'
if (Test-Path -LiteralPath $lcov) {
    $scanArgs += '-Dsonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info'
}
Push-Location -LiteralPath $toolRoot
try {
    & $scanner @scanArgs 1> (Join-Path $docs 'sonar-scan.log') 2>&1
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Variable token
}
Write-Output "Scanner exit code: $code; project: $key; log: $docs\sonar-scan.log"
exit $code
