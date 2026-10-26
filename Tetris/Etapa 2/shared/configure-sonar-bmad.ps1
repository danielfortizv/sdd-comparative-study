# Researcher-only local Sonar project/gate setup; never changes the built-in gate.
$ErrorActionPreference='Stop'
$stageRoot=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $stageRoot
$docs=Join-Path $stageRoot 'Bmad Method\docs\sonar-baseline'
New-Item -ItemType Directory -Force -Path $docs | Out-Null
$key='tetris-stage2-bmad'
$gateName='Tetris Stage 2 BMAD Controlled'
$base='http://127.0.0.1:9000'
$secret=(Get-Content -LiteralPath (Join-Path $caseRoot 'Etapa 1\_toolchain\sonar-token.txt') -Raw).Trim()
$headers=@{Authorization='Basic '+[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($secret+':'))}
Remove-Variable secret
function Save-Json($name,$value) {$value|ConvertTo-Json -Depth 50|Set-Content -LiteralPath (Join-Path $docs $name) -Encoding utf8}
function Get-Sonar($path) {Invoke-RestMethod -Uri ($base+$path) -Headers $headers -Method Get}
function Post-Sonar($path,$body) {Invoke-RestMethod -Uri ($base+$path) -Headers $headers -Method Post -Body $body}
$gateList=Get-Sonar '/api/qualitygates/list'
Save-Json 'quality-gates-before.json' $gateList
$builtInBefore=Get-Sonar '/api/qualitygates/show?name=Sonar%20way'
Save-Json 'built-in-gate-before.json' $builtInBefore
try {$component=Get-Sonar ('/api/components/show?component='+$key)}
catch {if ([int]$_.Exception.Response.StatusCode -eq 404) {$component=Post-Sonar '/api/projects/create' @{project=$key;name='Tetris Stage 2 BMAD';newCodeDefinitionType='PREVIOUS_VERSION'}} else {throw}}
Save-Json 'project.json' $component
if (-not ($gateList.qualitygates|Where-Object {$_.name -eq $gateName})) {
    Post-Sonar '/api/qualitygates/create' @{name=$gateName}|Out-Null
}
$initialGate=Get-Sonar ('/api/qualitygates/show?name='+[Uri]::EscapeDataString($gateName))
Save-Json 'dedicated-gate-initial.json' $initialGate
if ($initialGate.isBuiltIn -or $initialGate.name -ne $gateName) {throw 'Refusing to alter any gate other than the new dedicated BMAD gate.'}
$desired=@(@{metric='new_coverage';op='LT';error='80'},@{metric='new_duplicated_lines_density';op='GT';error='3'},@{metric='new_violations';op='GT';error='0'})
foreach($existing in $initialGate.conditions) {
    if ($existing.metric -notin $desired.metric) {
        Post-Sonar '/api/qualitygates/delete_condition' @{id=$existing.id}|Out-Null
    }
}
foreach($condition in $desired) {
    $matching=@($initialGate.conditions|Where-Object {$_.metric -eq $condition.metric})
    if ($matching.Count -eq 0) {
        Post-Sonar '/api/qualitygates/create_condition' @{gateName=$gateName;metric=$condition.metric;op=$condition.op;error=$condition.error}|Out-Null
    } elseif ($matching.Count -ne 1 -or $matching[0].op -ne $condition.op -or $matching[0].error -ne $condition.error) {
        throw 'Existing dedicated gate condition differs from the controlled threshold; refusing to overwrite it.'
    }
}
$gate=Get-Sonar ('/api/qualitygates/show?name='+[Uri]::EscapeDataString($gateName))
$actual=@($gate.conditions|ForEach-Object {"$($_.metric)|$($_.op)|$($_.error)"}|Sort-Object)
$expected=@('new_coverage|LT|80','new_duplicated_lines_density|GT|3','new_violations|GT|0')|Sort-Object
if ($actual.Count -ne 3 -or (Compare-Object $actual $expected)) {throw 'Dedicated gate does not have exactly the three controlled conditions; refusing association.'}
Post-Sonar '/api/qualitygates/select' @{projectKey=$key;gateName=$gateName}|Out-Null
Post-Sonar '/api/new_code_periods/set' @{project=$key;type='PREVIOUS_VERSION'}|Out-Null
$selection=Get-Sonar ('/api/qualitygates/get_by_project?project='+$key)
$newCode=Get-Sonar ('/api/new_code_periods/show?project='+$key)
$settings=Get-Sonar ('/api/settings/values?component='+$key+'&keys=sonar.qualitygate.ignoreSmallChanges,sonar.python.version')
$builtInAfter=Get-Sonar '/api/qualitygates/show?name=Sonar%20way'
Save-Json 'quality-gate-configuration.json' $gate
Save-Json 'project-gate-selection.json' $selection
Save-Json 'new-code-period.json' $newCode
Save-Json 'scanner-settings.json' $settings
Save-Json 'built-in-gate-after.json' $builtInAfter
$unchanged=($builtInBefore|ConvertTo-Json -Depth 50 -Compress) -eq ($builtInAfter|ConvertTo-Json -Depth 50 -Compress)
if (-not $unchanged) {throw 'Built-in gate configuration changed during setup.'}
$report=[ordered]@{researcher_created=$true;configured_at_utc=[DateTime]::UtcNow.ToString('o');project_key=$key;gate_name=$gateName;conditions=$gate.conditions;new_code_type=$newCode.type;baseline_project_version='1.0';final_project_version='2.0';built_in_gate_unchanged=$unchanged;baseline_frontend_lcov_available=$false;warning='The first baseline analysis can have no evaluated new-code conditions. Baseline gate status is not final Stage 2 acceptance.'}
Save-Json 'configuration-verification.json' $report
Remove-Variable headers
$report|ConvertTo-Json -Depth 20
