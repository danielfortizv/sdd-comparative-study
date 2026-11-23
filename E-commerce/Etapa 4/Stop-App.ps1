param([Parameter(Mandatory=$true)][ValidateSet('OpenSpec','Kiro','Tessl','SpecKit')][string]$Tool)
$ErrorActionPreference='Stop'
$folder=if($Tool -eq 'SpecKit'){'Spec Kit'}else{$Tool}
Push-Location -LiteralPath (Join-Path $PSScriptRoot $folder)
try {
    switch($Tool) {
        'OpenSpec' { & '.\Stop-Stage4.ps1' }
        'Kiro' { & '.\scripts\stop-stack.ps1' }
        'Tessl' { & '.\Stop-Services.ps1' }
        'SpecKit' { & '.\Stop-Services.ps1' }
    }
}
finally { Pop-Location }
