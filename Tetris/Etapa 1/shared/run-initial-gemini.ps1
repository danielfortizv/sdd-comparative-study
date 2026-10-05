param(
    [Parameter(Mandatory = $true)][string]$Workflow,
    [Parameter(Mandatory = $true)][string]$Label
)

$ErrorActionPreference = 'Stop'
$toolRoot = (Get-Location).Path
$experimentRoot = Split-Path -Parent $toolRoot
$seedPath = Join-Path $experimentRoot 'shared\initial-prompt.txt'
$geminiCmd = Join-Path $experimentRoot '_toolchain\node_modules\.bin\gemini.cmd'
$docs = Join-Path $toolRoot 'docs'
New-Item -ItemType Directory -Force -Path $docs | Out-Null

$env:GOOGLE_GENAI_USE_VERTEXAI = 'true'
$env:GOOGLE_CLOUD_PROJECT = 'project-e6384dd1-d4d3-4a03-948'
$env:GOOGLE_CLOUD_LOCATION = 'global'
$env:GEMINI_MODEL = 'gemini-3.5-flash'
$env:GOOGLE_APPLICATION_CREDENTIALS = Join-Path $env:APPDATA 'gcloud\application_default_credentials.json'
$env:GEMINI_CLI_TRUST_WORKSPACE = 'true'
$env:GEMINI_CLI_HOME = Join-Path $docs 'gemini-home'
$env:OPENSPEC_TELEMETRY = '0'
$env:PATH = (Join-Path $experimentRoot '_toolchain\node_modules\.bin') + ';' + (Join-Path $experimentRoot '_toolchain\venv\Scripts') + ';' + $env:PATH

if (-not (Test-Path -LiteralPath $env:GOOGLE_APPLICATION_CREDENTIALS)) {
    throw 'Application Default Credentials are missing.'
}

$seed = (Get-Content -LiteralPath $seedPath -Raw).TrimEnd()
Copy-Item -LiteralPath $seedPath -Destination (Join-Path $docs 'seed-submitted.txt') -Force
$request = $Workflow + ' ' + $seed
$started = Get-Date
$stdout = Join-Path $docs ($Label + '.stdout.json')
$stderr = Join-Path $docs ($Label + '.stderr.txt')
& $geminiCmd -m 'gemini-3.5-flash' -p $request -o json --approval-mode yolo 1> $stdout 2> $stderr
$code = $LASTEXITCODE
$ended = Get-Date
$run = [ordered]@{
    workflow = $Workflow
    seed_sha256 = (Get-FileHash -LiteralPath $seedPath -Algorithm SHA256).Hash
    model_requested = 'gemini-3.5-flash'
    project = 'project-e6384dd1-d4d3-4a03-948'
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
