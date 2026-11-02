param(
    [Parameter(Mandatory = $true)][ValidateSet('specify','plan','tasks','implement','clarify')][string]$Workflow,
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$Clarification,
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$toolRoot = (Get-Location).Path
$stageRoot = Split-Path -Parent $toolRoot
$caseRoot = Split-Path -Parent $stageRoot
$geminiCmd = Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\.bin\gemini.cmd'
$geminiEntry = Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\@google\gemini-cli\bundle\gemini.js'
$docs = Join-Path $toolRoot 'docs'
$seedPath = Join-Path $stageRoot 'shared\seed.md'

if (-not (Test-Path -LiteralPath $geminiCmd)) { throw 'Pinned Gemini CLI not found.' }
if (-not (Test-Path -LiteralPath (Join-Path $toolRoot '.specify\integration.json'))) { throw 'Spec Kit integration missing.' }
$seedLines = Get-Content -LiteralPath $seedPath -Encoding utf8 | Where-Object { $_ -match '^>' } | ForEach-Object { $_ -replace '^> ?', '' }
$seed = ($seedLines -join "`n").Trim()
if (-not $seed.StartsWith('Extend the existing Stage 1')) { throw 'Unexpected common seed.' }
$seedHash = (Get-FileHash -LiteralPath $seedPath -Algorithm SHA256).Hash
$stage2Feature = Get-ChildItem -LiteralPath (Join-Path $toolRoot 'specs') -Directory |
    Where-Object { $_.Name -match '^002-' } | Select-Object -First 1
if ($Workflow -ne 'specify' -and -not $stage2Feature) { throw 'Stage 2 Spec Kit feature directory missing.' }
$featureRelative = if ($stage2Feature) { 'specs/' + $stage2Feature.Name } else { 'specs/002-tetris-stage2-option-a' }

switch ($Workflow) {
    'specify' {
        $request = "/speckit.specify $seed`n`nSpec Kit-specific workflow instruction: create a new feature under specs/002-tetris-stage2-option-a, preserving specs/001-build-tetris-core. Treat this directory as an existing brownfield project. Do not create a Git branch, commit, push, or upload. Complete and validate the native specification on disk before any application code change."
    }
    'plan' {
        $request = "/speckit.plan Use the completed Stage 2 feature at $featureRelative and the unchanged common seed below. Complete the native plan, research, data model, contract and quickstart on disk. Do not edit application code yet, create a Git branch, commit, push, or upload.`n`n$seed"
    }
    'tasks' {
        $request = "/speckit.tasks Use $featureRelative and the unchanged common seed below. Write testable implementation and regression tasks, including Hold, preview, scoring, dynamic timer, race protection, tests, build and quality verification. Do not edit application code yet, create a Git branch, commit, push, or upload.`n`n$seed"
    }
    'implement' {
        $request = "/speckit.implement Implement every Stage 2 task in $featureRelative/tasks.md using the validated Spec Kit artifacts and the unchanged common seed below. Complete both backend and frontend, run tests and build, and check tasks only after verifying them. Do not create a Git branch, commit, push, or upload. The user has already authorized full local implementation.`n`n$seed"
    }
    'clarify' {
        if (-not $Clarification) { throw 'Clarification text is required.' }
        $request = "$Clarification`n`nCommon seed (unchanged):`n$seed"
    }
}

if ($Workflow -ne 'clarify' -and $Clarification) {
    $request += "`n`nRecorded workflow clarification: $Clarification"
}

New-Item -ItemType Directory -Force -Path $docs | Out-Null
$requestPath = Join-Path $docs "$Label.prompt.txt"
$rawRequestPath = Join-Path $docs "$Label.request.txt"
$stdout = Join-Path $docs "$Label.stdout.json"
$stderr = Join-Path $docs "$Label.stderr.txt"
$runPath = Join-Path $docs "$Label.run.json"
foreach ($p in @($requestPath,$rawRequestPath,$stdout,$stderr,$runPath)) { if (Test-Path -LiteralPath $p) { throw "Refusing to overwrite $p" } }
[IO.File]::WriteAllText($rawRequestPath, $request, [Text.UTF8Encoding]::new($false))
$submissionMethod = 'direct clarification prompt'
if ($Workflow -ne 'clarify') {
    $python = Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\python.exe'
    & $python (Join-Path $stageRoot 'shared\expand-spec-kit-command.py') --request $rawRequestPath --commands (Join-Path $toolRoot '.gemini\commands') --output $requestPath
    if ($LASTEXITCODE -ne 0) { throw 'Native command expansion failed.' }
    $request = [IO.File]::ReadAllText($requestPath, [Text.Encoding]::UTF8)
    $submissionMethod = 'installed native TOML prompt expanded with complete multiline arguments'
} else {
    [IO.File]::WriteAllText($requestPath, $request, [Text.UTF8Encoding]::new($false))
}
if ($Workflow -eq 'specify') { [IO.File]::WriteAllText((Join-Path $docs 'seed-submitted.txt'), $seed, [Text.UTF8Encoding]::new($false)) }

$env:GOOGLE_GENAI_USE_VERTEXAI = 'true'
$env:GOOGLE_CLOUD_PROJECT = 'project-e6384dd1-d4d3-4a03-948'
$env:GOOGLE_CLOUD_LOCATION = 'global'
$env:GEMINI_MODEL = 'gemini-3.5-flash'
$env:GOOGLE_APPLICATION_CREDENTIALS = Join-Path $env:APPDATA 'gcloud\application_default_credentials.json'
$env:GEMINI_CLI_TRUST_WORKSPACE = 'true'
$env:GEMINI_CLI_HOME = Join-Path $docs 'gemini-home'
$env:PATH = (Join-Path $caseRoot 'Etapa 1\_toolchain\node_modules\.bin') + ';' + (Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts') + ';' + $env:PATH
if (-not (Test-Path -LiteralPath $env:GOOGLE_APPLICATION_CREDENTIALS)) { throw 'Application Default Credentials missing.' }

$started = Get-Date
[ordered]@{
    label=$Label; workflow=$Workflow; started=$started.ToString('o')
    prompt_sha256=(Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash
    seed_sha256=$seedHash; submission_method=$submissionMethod
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $docs "$Label.started.json") -Encoding utf8
if ($Resume) {
    & node $geminiEntry --resume latest -m 'gemini-3.5-flash' --approval-mode yolo --output-format json -p $request 1> $stdout 2> $stderr
} else {
    & node $geminiEntry -m 'gemini-3.5-flash' --approval-mode yolo --output-format json -p $request 1> $stdout 2> $stderr
}
$code = $LASTEXITCODE
$ended = Get-Date
$run = [ordered]@{
    workflow = $Workflow
    submission_method = $submissionMethod
    launcher = 'node direct to pinned Gemini CLI entrypoint, avoiding cmd.exe length limit'
    label = $Label
    prompt_sha256 = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash
    seed_sha256 = $seedHash
    requested_model = 'gemini-3.5-flash'
    cli_version = '0.60.0'
    spec_kit_version = '1.0.12'
    started = $started.ToString('o')
    ended = $ended.ToString('o')
    duration_seconds = [Math]::Round(($ended-$started).TotalSeconds,3)
    exit_code = $code
    stdout = $stdout
    stderr = $stderr
}
$run | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $runPath -Encoding utf8
& (Join-Path $caseRoot 'Etapa 1\_toolchain\venv\Scripts\python.exe') (Join-Path $stageRoot 'shared\archive-spec-kit-transcripts.py')
Write-Output ($run | ConvertTo-Json -Compress -Depth 4)
exit $code
