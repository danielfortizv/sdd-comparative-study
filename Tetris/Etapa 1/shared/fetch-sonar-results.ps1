param(
    [Parameter(Mandatory = $true)][string]$Tool,
    [Parameter(Mandatory = $true)][string]$ProjectKey
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docs = Join-Path (Join-Path $root $Tool) 'docs'
New-Item -ItemType Directory -Force -Path $docs | Out-Null
$token = (Get-Content -LiteralPath (Join-Path $root '_toolchain\sonar-token.txt') -Raw).Trim()
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${token}:"))
$headers = @{ Authorization = "Basic $basic" }
$base = 'http://127.0.0.1:9000'
$key = [Uri]::EscapeDataString($ProjectKey)
$metricKeys = 'bugs,code_smells,cognitive_complexity,complexity,coverage,duplicated_lines_density,lines,ncloc,reliability_rating,security_rating,sqale_index,sqale_rating,vulnerabilities'
$queries = @{
    'sonar-metrics.json' = "$base/api/measures/component?component=$key&metricKeys=$metricKeys"
    'sonar-issues.json' = "$base/api/issues/search?componentKeys=$key&ps=500"
    'sonar-quality-gate.json' = "$base/api/qualitygates/project_status?projectKey=$key"
    'sonar-task.json' = "$base/api/ce/component?component=$key"
}
foreach ($entry in $queries.GetEnumerator()) {
    $response = Invoke-RestMethod -Uri $entry.Value -Headers $headers -Method Get
    $response | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath (Join-Path $docs $entry.Key) -Encoding utf8
}
$metrics = (Get-Content -LiteralPath (Join-Path $docs 'sonar-metrics.json') -Raw | ConvertFrom-Json).component.measures
$gate = (Get-Content -LiteralPath (Join-Path $docs 'sonar-quality-gate.json') -Raw | ConvertFrom-Json).projectStatus.status
$summary = [ordered]@{ project = $ProjectKey; gate = $gate }
foreach ($measure in $metrics) { $summary[$measure.metric] = $measure.value }
Write-Output ($summary | ConvertTo-Json -Compress)
