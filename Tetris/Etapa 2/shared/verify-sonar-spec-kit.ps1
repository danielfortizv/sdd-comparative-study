param()

# Researcher evidence helper: verify the exact submitted analysis before reporting a gate.
$ErrorActionPreference = 'Stop'
$stageRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Split-Path -Parent $stageRoot
$toolRoot = Join-Path $stageRoot 'Spec Kit'
$docs = Join-Path $toolRoot 'docs'
$taskFile = Join-Path $toolRoot '.sonar\report-task.txt'
$taskProperties = @{}
Get-Content -LiteralPath $taskFile | ForEach-Object {
    $parts = $_ -split '=',2
    if ($parts.Length -eq 2) { $taskProperties[$parts[0]] = $parts[1] }
}
if ($taskProperties.projectKey -ne 'tetris-stage2-speckit' -or -not $taskProperties.ceTaskId) {
    throw 'Unexpected project or missing analysis task.'
}
$token = (Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${token}:"))
Remove-Variable token
$headers = @{ Authorization = "Basic $basic" }
$taskId = [Uri]::EscapeDataString($taskProperties.ceTaskId)
$deadline = (Get-Date).AddSeconds(55)
do {
    $task = Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/ce/task?id=$taskId" -Headers $headers
    if ($task.task.status -notin @('PENDING','IN_PROGRESS')) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
$task | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $docs 'sonar-exact-task.json') -Encoding utf8
if ($task.task.status -ne 'SUCCESS' -or -not $task.task.analysisId) {
    throw "Submitted Sonar analysis is not complete: $($task.task.status)"
}
$analysisId = [Uri]::EscapeDataString($task.task.analysisId)
$gate = Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/qualitygates/project_status?analysisId=$analysisId" -Headers $headers
$gate | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $docs 'sonar-exact-quality-gate.json') -Encoding utf8
$verification = [ordered]@{
    verified_at_utc = [DateTime]::UtcNow.ToString('o')
    project_key = $taskProperties.projectKey
    report_task_sha256 = (Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash
    ce_task_id = $task.task.id
    ce_status = $task.task.status
    analysis_id = $task.task.analysisId
    submitted_at = $task.task.submittedAt
    executed_at = $task.task.executedAt
    gate_status = $gate.projectStatus.status
    gate_conditions = $gate.projectStatus.conditions
    coverage_inputs = @(
        foreach ($relative in @('docs/coverage.xml','frontend/coverage/lcov.info')) {
            $path = Join-Path $toolRoot $relative
            [ordered]@{
                path = $relative
                exists = (Test-Path -LiteralPath $path)
                sha256 = if (Test-Path -LiteralPath $path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash } else { $null }
                last_write_time_utc = if (Test-Path -LiteralPath $path) { (Get-Item -LiteralPath $path).LastWriteTimeUtc.ToString('o') } else { $null }
            }
        }
    )
}
Remove-Variable basic,headers
$verification | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $docs 'sonar-verification.json') -Encoding utf8
Write-Output ($verification | ConvertTo-Json -Depth 30)
