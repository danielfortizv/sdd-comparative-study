param()

$ErrorActionPreference = 'Stop'
$stageRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Split-Path -Parent $stageRoot
$docs = Join-Path $stageRoot 'Bmad Method\docs'
$tokenPath = Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt'
$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${token}:"))
Remove-Variable token
$headers = @{ Authorization = "Basic $basic" }
$base = 'http://127.0.0.1:9000'
$key = [Uri]::EscapeDataString('tetris-stage2-bmad')
$metricKeys = 'bugs,code_smells,cognitive_complexity,complexity,coverage,duplicated_lines_density,lines,ncloc,reliability_rating,security_hotspots,security_rating,sqale_index,sqale_rating,vulnerabilities'
$queries = @{
    'sonar-metrics.json' = "$base/api/measures/component?component=$key&metricKeys=$metricKeys"
    'sonar-issues.json' = "$base/api/issues/search?componentKeys=$key&ps=500"
    'sonar-open-issues.json' = "$base/api/issues/search?componentKeys=$key&resolved=false&ps=500"
    'sonar-quality-gate.json' = "$base/api/qualitygates/project_status?projectKey=$key"
    'sonar-task.json' = "$base/api/ce/component?component=$key"
}
foreach ($entry in $queries.GetEnumerator()) {
    $response = Invoke-RestMethod -Uri $entry.Value -Headers $headers -Method Get
    $response | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath (Join-Path $docs $entry.Key) -Encoding utf8
}
Remove-Variable basic
$measures = (Get-Content -LiteralPath (Join-Path $docs 'sonar-metrics.json') -Raw | ConvertFrom-Json).component.measures
$gate = (Get-Content -LiteralPath (Join-Path $docs 'sonar-quality-gate.json') -Raw | ConvertFrom-Json).projectStatus.status
$summary = [ordered]@{ project = 'tetris-stage2-bmad'; gate = $gate }
foreach ($measure in $measures) { $summary[$measure.metric] = $measure.value }
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $docs 'sonar-summary.json') -Encoding utf8
Write-Output ($summary | ConvertTo-Json -Compress)
