param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$Workflow,
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$toolRoot = (Get-Location).Path
$experimentRoot = Split-Path -Parent $toolRoot
$docs = Join-Path $toolRoot 'docs'
New-Item -ItemType Directory -Force -Path $docs | Out-Null
$seedPath = Join-Path $experimentRoot 'shared\initial-prompt.txt'
$seed = (Get-Content -LiteralPath $seedPath -Raw).TrimEnd()
Copy-Item -LiteralPath $seedPath -Destination (Join-Path $docs 'seed-submitted.txt') -Force
$request = $Workflow + ' ' + $seed + ' Do not create Git commits or push any branch.'
Set-Content -LiteralPath (Join-Path $docs ($Label + '.prompt.txt')) -Value $request -Encoding utf8
$stdout = Join-Path $docs ($Label + '.stdout.jsonl')
$stderr = Join-Path $docs ($Label + '.stderr.txt')
$kiro = Join-Path $env:LOCALAPPDATA 'Kiro-Cli\kiro-cli.exe'
$started = Get-Date
if ($Resume) {
    & $kiro chat --v3 --mode spec --resume --no-interactive --trust-all-tools --output-format stream-json $request 1> $stdout 2> $stderr
} else {
    & $kiro chat --v3 --mode spec --no-interactive --trust-all-tools --output-format stream-json $request 1> $stdout 2> $stderr
}
$code = $LASTEXITCODE
$ended = Get-Date
$run = [ordered]@{
    workflow = $Workflow
    seed_sha256 = (Get-FileHash -LiteralPath $seedPath -Algorithm SHA256).Hash
    started = $started.ToString('o')
    ended = $ended.ToString('o')
    duration_seconds = [Math]::Round(($ended - $started).TotalSeconds, 3)
    exit_code = $code
    stdout = $stdout
    stderr = $stderr
}
$run | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $docs ($Label + '.run.json')) -Encoding utf8
Write-Output ($run | ConvertTo-Json -Compress -Depth 5)
exit $code
