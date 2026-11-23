param([Parameter(Mandatory=$true)][ValidateSet('OpenSpec','Kiro','Tessl','SpecKit')][string]$Tool)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'LocalBroker\Start-LocalBroker.ps1')
$folder=if($Tool -eq 'SpecKit'){'Spec Kit'}else{$Tool}
$appRoot=Join-Path $PSScriptRoot $folder
Push-Location -LiteralPath $appRoot
try {
    switch($Tool) {
        'OpenSpec' { & '.\Start-Stage4.ps1' }
        'Kiro' { & '.\scripts\start-stack.ps1' -Frontend }
        'Tessl' { & '.\Start-Services.ps1' }
        'SpecKit' { & '.\Start-Services.ps1' -Frontend }
    }
    $runtime=Get-Content 'stage4-runtime.json' -Raw | ConvertFrom-Json
    Write-Host "Abrir $Tool en http://127.0.0.1:$($runtime.frontend_port)"
}
finally { Pop-Location }
