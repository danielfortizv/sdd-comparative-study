# Researcher evidence only: bind and freeze the first Tessl baseline analysis.
$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$root=Join-Path $stageRoot 'Tessl'
$docs=Join-Path $root 'docs'
$baseline=Join-Path $docs 'sonar-baseline'
$secret=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1/_toolchain/sonar-token.txt') -Raw).Trim()
$headers=@{Authorization='Basic '+[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($secret+':'))}
Remove-Variable secret
$properties=@{}
Get-Content -LiteralPath (Join-Path $root '.sonar/report-task.txt') | ForEach-Object {$p=$_ -split '=',2; if($p.Length -eq 2){$properties[$p[0]]=$p[1]}}
if($properties.projectKey -ne 'tetris-stage2-tessl'){throw 'Unexpected project'}
$task=Invoke-RestMethod -Uri ($properties.serverUrl+'/api/ce/task?id='+[Uri]::EscapeDataString($properties.ceTaskId)) -Headers $headers
if($task.task.status -ne 'SUCCESS' -or -not $task.task.analysisId){throw 'Baseline CE task not completed'}
$gate=Invoke-RestMethod -Uri ($properties.serverUrl+'/api/qualitygates/project_status?analysisId='+[Uri]::EscapeDataString($task.task.analysisId)) -Headers $headers
$task | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $baseline 'sonar-exact-task.json') -Encoding utf8
$gate | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $baseline 'sonar-exact-quality-gate.json') -Encoding utf8
foreach($name in @('sonar-summary.json','sonar-metrics.json','sonar-issues.json','sonar-open-issues.json','sonar-quality-gate.json','sonar-task.json')) {
    Copy-Item -LiteralPath (Join-Path $docs $name) -Destination (Join-Path $baseline $name)
}
Copy-Item -LiteralPath (Join-Path $root '.sonar/report-task.txt') -Destination (Join-Path $baseline 'report-task.txt')
$summary=Get-Content -LiteralPath (Join-Path $baseline 'sonar-summary.json') -Raw | ConvertFrom-Json
$record=[ordered]@{researcher_created=$true;verified_at_utc=[DateTime]::UtcNow.ToString('o');scope='Own Stage1 code copied into Tessl Stage2; not Stage2 acceptance';project_key=$properties.projectKey;version='1.0';ce_task_id=$task.task.id;ce_status=$task.task.status;analysis_id=$task.task.analysisId;gate_status=$gate.projectStatus.status;evaluated_new_code_conditions=@($gate.projectStatus.conditions).Count;coverage_xml='docs/baseline-coverage.xml';coverage_sha256=(Get-FileHash -LiteralPath (Join-Path $docs 'baseline-coverage.xml')).Hash;frontend_lcov_available=$false;measures=$summary;finding_note='14 inherited code smells and 1 inherited python:S2245 vulnerability remain open; no suppression or generator change. New-code baseline gate has no evaluated conditions and is not final acceptance.';scanner_incident='First researcher launcher failed before scanner analysis with Unexpected argument 1.0. Original failure retained in attempt-1-launcher-argument-failure; corrected argument grouping, no app changes.'}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $baseline 'baseline-verification.json') -Encoding utf8
Remove-Variable headers
$record | ConvertTo-Json -Depth 10
