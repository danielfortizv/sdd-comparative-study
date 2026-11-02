param(
    [Parameter(Mandatory = $true)][ValidateSet('propose','apply','update','clarify')][string]$Workflow,
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$Clarification,
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$toolRoot = (Get-Location).Path
$stageRoot = Split-Path -Parent $toolRoot
$caseRoot = Split-Path -Parent $stageRoot
$geminiCmd = Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\.bin\gemini.cmd'
$openspecCmd = Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\.bin\openspec.cmd'
$docs = Join-Path $toolRoot 'docs'
$seedPath = Join-Path $stageRoot 'shared\seed.md'

if (-not (Test-Path -LiteralPath $geminiCmd)) { throw 'Pinned Gemini CLI not found.' }
if (-not (Test-Path -LiteralPath $openspecCmd)) { throw 'Pinned OpenSpec CLI not found.' }
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot 'openspec\config.yaml'))) { throw 'OpenSpec root missing.' }

$seedLines = Get-Content -LiteralPath $seedPath -Encoding utf8 | Where-Object { $_ -match '^>' } | ForEach-Object { $_ -replace '^> ?', '' }
$seed = ($seedLines -join "`n").Trim()
if (-not $seed.StartsWith('Extend the existing Stage 1')) { throw 'Unexpected common seed.' }
$seedHash = (Get-FileHash -LiteralPath $seedPath -Algorithm SHA256).Hash

switch ($Workflow) {
    'propose' { $nativeCommand = '/opsx:propose tetris-stage2-option-a' }
    'apply'   { $nativeCommand = '/opsx:apply tetris-stage2-option-a' }
    'update'  { $nativeCommand = '/opsx:update tetris-stage2-option-a' }
    'clarify' { $nativeCommand = '' }
}
if ($Workflow -eq 'clarify') {
    if (-not $Clarification) { throw 'Clarification text is required.' }
    $request = "$Clarification`n`nCommon seed (unchanged):`n$seed"
} elseif ($Workflow -eq 'propose') {
    $request = "$nativeCommand`n`n$seed"
} elseif ($Workflow -eq 'apply') {
    $request = "$nativeCommand`n`n$seed`n`nThe user has already authorized full local implementation after planning. Use the validated native change artifacts as the source of truth; preserve the existing Stage 1 restart behavior, which creates a new session via POST /api/games. Complete all tasks, verify with tests and build, and mark task checkboxes only when verified. Do not ask for approval, create a Git commit, or push anything."
} else {
    $request = "$nativeCommand`n`nContinue the exact common Stage 2 option A seed already submitted in this tool directory. Do not broaden scope. Update native specs before any code correction. Complete the requested native workflow."
}

New-Item -ItemType Directory -Force -Path $docs | Out-Null
$requestPath = Join-Path $docs "$Label.prompt.txt"
$stdout = Join-Path $docs "$Label.stdout.json"
$stderr = Join-Path $docs "$Label.stderr.txt"
$runPath = Join-Path $docs "$Label.run.json"
foreach ($p in @($requestPath,$stdout,$stderr,$runPath)) { if (Test-Path -LiteralPath $p) { throw "Refusing to overwrite $p" } }
[IO.File]::WriteAllText($requestPath, $request, [Text.UTF8Encoding]::new($false))
if ($Workflow -eq 'propose') { [IO.File]::WriteAllText((Join-Path $docs 'seed-submitted.txt'), $seed, [Text.UTF8Encoding]::new($false)) }

$env:GOOGLE_GENAI_USE_VERTEXAI = 'true'
$env:GOOGLE_CLOUD_PROJECT = 'project-e6384dd1-d4d3-4a03-948'
$env:GOOGLE_CLOUD_LOCATION = 'global'
$env:GEMINI_MODEL = 'gemini-3.5-flash'
$env:GOOGLE_APPLICATION_CREDENTIALS = Join-Path $env:APPDATA 'gcloud\application_default_credentials.json'
$env:GEMINI_CLI_TRUST_WORKSPACE = 'true'
$env:GEMINI_CLI_HOME = Join-Path $docs 'gemini-home'
$env:OPENSPEC_TELEMETRY = '0'
$env:PATH = (Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\.bin') + ';' + (Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts') + ';' + $env:PATH
if (-not (Test-Path -LiteralPath $env:GOOGLE_APPLICATION_CREDENTIALS)) { throw 'Application Default Credentials are missing.' }

$started = Get-Date
if ($Resume) {
    & $geminiCmd --resume latest -m 'gemini-3.5-flash' --approval-mode yolo --output-format json -p $request 1> $stdout 2> $stderr
} else {
    & $geminiCmd -m 'gemini-3.5-flash' --approval-mode yolo --output-format json -p $request 1> $stdout 2> $stderr
}
$code = $LASTEXITCODE
$ended = Get-Date
$run = [ordered]@{
    workflow = $Workflow
    label = $Label
    prompt_sha256 = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash
    seed_sha256 = $seedHash
    requested_model = 'gemini-3.5-flash'
    cli_version = '0.60.0'
    openspec_version = '1.13.2'
    project = 'project-e6384dd1-d4d3-4a03-948'
    started = $started.ToString('o')
    ended = $ended.ToString('o')
    duration_seconds = [Math]::Round(($ended-$started).TotalSeconds,3)
    exit_code = $code
    stdout = $stdout
    stderr = $stderr
}
$run | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $runPath -Encoding utf8
Write-Output ($run | ConvertTo-Json -Compress -Depth 4)
exit $code
