param([switch]$Baseline)

# Verify the exact CE submission, not merely scanner exit or a previous gate.
$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$toolRoot=Join-Path $stageRoot 'Kiro'
$docs=Join-Path $toolRoot 'docs'
if ($Baseline) {$docs=Join-Path $docs 'sonar-baseline'}
$taskFile=if ($Baseline) {Join-Path $docs 'report-task.txt'} else {Join-Path $toolRoot '.sonar\report-task.txt'}
$properties=@{}
Get-Content -LiteralPath $taskFile|ForEach-Object {$parts=$_ -split '=',2;if($parts.Length -eq 2){$properties[$parts[0]]=$parts[1]}}
if ($properties.projectKey -ne 'tetris-stage2-kiro' -or -not $properties.ceTaskId) {throw 'Unexpected project or missing CE submission.'}
$token=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$basic=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${token}:"))
Remove-Variable token
$headers=@{Authorization="Basic $basic"}
$taskId=[Uri]::EscapeDataString($properties.ceTaskId)
$deadline=(Get-Date).AddSeconds(55)
do {
 $task=Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/ce/task?id=$taskId" -Headers $headers
 if ($task.task.status -notin @('PENDING','IN_PROGRESS')) {break}
 Start-Sleep -Seconds 2
} while((Get-Date) -lt $deadline)
$task|ConvertTo-Json -Depth 30|Set-Content -LiteralPath (Join-Path $docs 'sonar-exact-task.json') -Encoding utf8
if ($task.task.status -ne 'SUCCESS' -or -not $task.task.analysisId) {throw "Submitted Sonar analysis incomplete: $($task.task.status)"}
$analysisId=[Uri]::EscapeDataString($task.task.analysisId)
$gate=Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/qualitygates/project_status?analysisId=$analysisId" -Headers $headers
$gate|ConvertTo-Json -Depth 30|Set-Content -LiteralPath (Join-Path $docs 'sonar-exact-quality-gate.json') -Encoding utf8
$coverage=if($Baseline){'docs/baseline-coverage.xml'}else{'docs/coverage.xml'}
$verification=[ordered]@{researcher_created=$true;verified_at_utc=[DateTime]::UtcNow.ToString('o');project_key=$properties.projectKey;baseline=[bool]$Baseline;
 report_task_sha256=(Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash;
 ce_task_id=$task.task.id;ce_status=$task.task.status;analysis_id=$task.task.analysisId;submitted_at=$task.task.submittedAt;executed_at=$task.task.executedAt;
 gate_status=$gate.projectStatus.status;gate_conditions=$gate.projectStatus.conditions;
 baseline_is_final_stage2_acceptance=$false;
 coverage_inputs=@(foreach($relative in @($coverage,'frontend/coverage/lcov.info')) {
  $path=Join-Path $toolRoot $relative
  [ordered]@{path=$relative;exists=(Test-Path -LiteralPath $path);
  sha256=if(Test-Path -LiteralPath $path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}else{$null};
  last_write_time_utc=if(Test-Path -LiteralPath $path){(Get-Item -LiteralPath $path).LastWriteTimeUtc.ToString('o')}else{$null}}
 })}
Remove-Variable basic,headers
$verification|ConvertTo-Json -Depth 30|Set-Content -LiteralPath (Join-Path $docs 'sonar-verification.json') -Encoding utf8
$verification|ConvertTo-Json -Depth 30
