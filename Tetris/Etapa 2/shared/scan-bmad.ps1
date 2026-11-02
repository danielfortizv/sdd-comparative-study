param([switch]$Baseline)

# Researcher scanner adapter. Test layout and creation status belong to BMAD.
$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$toolRoot=Join-Path $stageRoot 'Bmad Method'
$docs=Join-Path $toolRoot 'docs'
$evidence=if ($Baseline) {Join-Path $docs 'sonar-baseline'} else {$docs}
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
# Preserve prior scanner evidence before a new attempt overwrites current paths.
if (-not $Baseline -and (Test-Path -LiteralPath (Join-Path $docs 'scan-command.json'))) {
 $attemptArchive=Join-Path $docs ('sonar-attempts/before-'+(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffffffZ'))
 New-Item -ItemType Directory -Path $attemptArchive -Force | Out-Null
 Get-ChildItem -LiteralPath $docs -File | Where-Object {$_.Name -like 'sonar-*' -or $_.Name -eq 'scan-command.json'} | Copy-Item -Destination $attemptArchive
 foreach ($relative in @('.sonar/report-task.txt','docs/coverage.xml','frontend/coverage/lcov.info')) {
  $priorPath=Join-Path $toolRoot $relative
  if (Test-Path -LiteralPath $priorPath) {Copy-Item -LiteralPath $priorPath -Destination (Join-Path $attemptArchive ([IO.Path]::GetFileName($priorPath)))}
 }
}
$coverage=if ($Baseline) {'docs/baseline-coverage.xml'} else {'docs/coverage.xml'}
$scanner=Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\pysonar.exe'
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot $coverage))) {throw 'Coverage XML is missing.'}
$token=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$env:SONAR_USER_HOME=Join-Path $toolRoot '.sonar-user-home'
$scanArgs=@('--token',$token,'--sonar-project-key','tetris-stage2-bmad',
 '--sonar-project-name','Tetris Stage 2 BMAD','--sonar-host-url','http://127.0.0.1:9000',
 '--sonar-sources','backend/app,frontend/src','--sonar-tests','backend/app/tests,frontend/src',
 '--sonar-python-coverage-report-paths',$coverage,
 '-Dsonar.test.inclusions=backend/app/tests/**,frontend/src/**/*.test.ts,frontend/src/**/*.test.tsx',
 '-Dsonar.exclusions=frontend/src/**/*.test.ts,frontend/src/**/*.test.tsx',
 ('-Dsonar.projectVersion='+$(if ($Baseline) {'1.0'} else {'2.0'})))
$lcov=Join-Path $toolRoot 'frontend/coverage/lcov.info'
if (Test-Path -LiteralPath $lcov) {$scanArgs+='-Dsonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info'}
elseif (-not $Baseline) {throw 'Final frontend LCOV is missing.'}
$start=Get-Date
function Get-BMADScanSourceHashes {
 $hashRows=@()
 foreach ($folder in @('backend/app','frontend/src')) {
  $hashRows+=Get-ChildItem -LiteralPath (Join-Path $toolRoot $folder) -Recurse -File |
   Where-Object {$_.Extension -in @('.py','.ts','.tsx','.js','.jsx','.css') -and $_.FullName -notlike '*\__pycache__\*'} |
   Sort-Object FullName | ForEach-Object {
    [ordered]@{path=$_.FullName.Substring($toolRoot.Length+1).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
   }
 }
 return $hashRows
}
$sourceBefore=@(Get-BMADScanSourceHashes)
Push-Location -LiteralPath $toolRoot
try {& $scanner @scanArgs 1> (Join-Path $evidence 'sonar-scan.log') 2>&1; $code=$LASTEXITCODE}
finally {Pop-Location; Remove-Variable token}
$sourceAfter=@(Get-BMADScanSourceHashes)
$sourceStable=($null -eq (Compare-Object @($sourceBefore | ForEach-Object {$_.path+' '+$_.sha256}) @($sourceAfter | ForEach-Object {$_.path+' '+$_.sha256})))
[ordered]@{started=$start.ToString('o');ended=(Get-Date).ToString('o');exit_code=$code;
 project='tetris-stage2-bmad';baseline=[bool]$Baseline;coverage_xml=$coverage;
 frontend_lcov_present=(Test-Path -LiteralPath $lcov);test_classification='backend/app/tests/** and frontend/src/**/*.test.{ts,tsx}';
 source_excludes='frontend/src/**/*.test.{ts,tsx}';
 coverage_sha256=(Get-FileHash -LiteralPath (Join-Path $toolRoot $coverage) -Algorithm SHA256).Hash
 frontend_lcov_sha256=$(if (Test-Path -LiteralPath $lcov) {(Get-FileHash -LiteralPath $lcov -Algorithm SHA256).Hash} else {$null})
 source_unchanged_during_scan=$sourceStable;source_hashes_before=$sourceBefore;source_hashes_after=$sourceAfter
 } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $evidence 'scan-command.json') -Encoding utf8
Write-Output "Scanner exit code: $code; project: tetris-stage2-bmad; baseline: $Baseline"
exit $code
