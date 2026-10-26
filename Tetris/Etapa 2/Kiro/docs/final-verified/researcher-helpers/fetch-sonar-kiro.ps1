param([switch]$Baseline)

$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$docs=Join-Path $stageRoot 'Kiro\docs'
if ($Baseline) {$docs=Join-Path $docs 'sonar-baseline'}
New-Item -ItemType Directory -Force -Path $docs | Out-Null
$token=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$basic=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${token}:"))
Remove-Variable token
$headers=@{Authorization="Basic $basic"}
$base='http://127.0.0.1:9000'
$key='tetris-stage2-kiro'
$metricKeys='bugs,code_smells,cognitive_complexity,complexity,coverage,duplicated_lines_density,lines,ncloc,reliability_rating,security_hotspots,security_rating,sqale_index,sqale_rating,vulnerabilities'
$queries=@{
 'sonar-metrics.json'="$base/api/measures/component?component=$key&metricKeys=$metricKeys"
 'sonar-issues.json'="$base/api/issues/search?componentKeys=$key&ps=500"
 'sonar-open-issues.json'="$base/api/issues/search?componentKeys=$key&resolved=false&ps=500"
 'sonar-quality-gate.json'="$base/api/qualitygates/project_status?projectKey=$key"
 'sonar-task.json'="$base/api/ce/component?component=$key"
 'sonar-analysis-history.json'="$base/api/project_analyses/search?project=$key&ps=100"
}
foreach($entry in $queries.GetEnumerator()) {
 Invoke-RestMethod -Uri $entry.Value -Headers $headers -Method Get|ConvertTo-Json -Depth 50|Set-Content -LiteralPath (Join-Path $docs $entry.Key) -Encoding utf8
}
Remove-Variable basic,headers
$measures=(Get-Content -LiteralPath (Join-Path $docs 'sonar-metrics.json') -Raw|ConvertFrom-Json).component.measures
$gate=(Get-Content -LiteralPath (Join-Path $docs 'sonar-quality-gate.json') -Raw|ConvertFrom-Json).projectStatus.status
$summary=[ordered]@{researcher_created=$true;fetched_at_utc=[DateTime]::UtcNow.ToString('o');project=$key;baseline=[bool]$Baseline;gate=$gate}
foreach($measure in $measures) {$summary[$measure.metric]=$measure.value}
$summary|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $docs 'sonar-summary.json') -Encoding utf8
$summary|ConvertTo-Json -Compress
