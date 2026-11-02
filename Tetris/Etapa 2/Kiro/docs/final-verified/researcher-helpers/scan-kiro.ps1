param([switch]$Baseline)

# Researcher scanner: no application/test/specification edits or issue suppressions.
$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$toolRoot=Join-Path $stageRoot 'Kiro'
$docs=Join-Path $toolRoot 'docs'
$evidence=if ($Baseline) {Join-Path $docs 'sonar-baseline'} else {$docs}
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$coverage=if ($Baseline) {'docs/baseline-coverage.xml'} else {'docs/coverage.xml'}
$projectVersion=if ($Baseline) {'1.0'} else {'2.0'}
$scanner=Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\pysonar.exe'
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot $coverage))) {throw 'Coverage XML is missing.'}
$lcov=Join-Path $toolRoot 'frontend\coverage\lcov.info'
if ($Baseline -and (Test-Path -LiteralPath $lcov)) {throw 'Unexpected frontend LCOV at the untouched baseline; refusing to mix later evidence.'}
if (-not $Baseline -and -not (Test-Path -LiteralPath $lcov)) {throw 'Final frontend LCOV is missing.'}
$token=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$env:SONAR_USER_HOME=Join-Path $toolRoot '.sonar-user-home'
$scanArgs=@('--token',$token,'--sonar-project-key','tetris-stage2-kiro',
 '--sonar-project-name','Tetris Stage 2 Kiro','--sonar-host-url','http://127.0.0.1:9000',
 '--sonar-sources','backend/app,frontend/src','--sonar-tests','backend/tests,frontend/src',
 '--sonar-python-coverage-report-paths',$coverage,
 '-Dsonar.test.inclusions=backend/tests/**,frontend/src/**/*.test.ts,frontend/src/**/*.test.tsx',
 '-Dsonar.exclusions=frontend/src/**/*.test.ts,frontend/src/**/*.test.tsx',
 ('-Dsonar.projectVersion='+$projectVersion))
if (-not $Baseline) {$scanArgs+='-Dsonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info'}
$start=Get-Date
Push-Location -LiteralPath $toolRoot
try {& $scanner @scanArgs 1> (Join-Path $evidence 'sonar-scan.log') 2>&1; $code=$LASTEXITCODE}
finally {Pop-Location; Remove-Variable token}
$taskFile=Join-Path $toolRoot '.sonar\report-task.txt'
if ($code -eq 0 -and (Test-Path -LiteralPath $taskFile)) {
    Copy-Item -LiteralPath $taskFile -Destination (Join-Path $evidence 'report-task.txt') -Force
}
[ordered]@{researcher_created=$true;started=$start.ToString('o');ended=(Get-Date).ToString('o');exit_code=$code;
 project='tetris-stage2-kiro';project_version=$projectVersion;baseline=[bool]$Baseline;coverage_xml=$coverage;
 frontend_lcov_present=(Test-Path -LiteralPath $lcov);
 baseline_frontend_coverage_limitation=if ($Baseline) {'No inherited frontend test framework/LCOV; global Sonar coverage includes uninstrumented frontend lines.'} else {$null};
 test_classification='backend/tests/** and frontend/src/**/*.test.{ts,tsx}';
 source_excludes='Only frontend/src/**/*.test.{ts,tsx}, classified as tests; no production issue/coverage exclusions';
 coverage_sha256=(Get-FileHash -LiteralPath (Join-Path $toolRoot $coverage) -Algorithm SHA256).Hash
 } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidence 'scan-command.json') -Encoding utf8
Write-Output "Scanner exit code: $code; project: tetris-stage2-kiro; baseline: $Baseline; project version: $projectVersion"
exit $code
