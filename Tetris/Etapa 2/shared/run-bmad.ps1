param([Parameter(Mandatory=$true)][string]$Label,[Parameter(Mandatory=$true)][string]$Instructions,[string]$Category='planning',[string]$QaIntent)
# Researcher launcher: exact seed, isolated account and bounded native sessions.
$ErrorActionPreference='Stop'
$toolRoot=(Get-Location).Path
if ((Split-Path -Leaf $toolRoot) -ne 'Bmad Method') {throw 'Run only inside Stage2/Bmad Method.'}
$stageRoot=Split-Path -Parent $toolRoot
$caseRoot=Split-Path -Parent $stageRoot
$docs=Join-Path $toolRoot 'docs'
$seedPath=Join-Path $stageRoot 'shared/seed.md'
if ((Get-FileHash -LiteralPath $seedPath).Hash -ne '63919779DD4104076FBABCB130CE296A160FA840E0B4755A2AA5D90757ADA8EF') {throw 'Frozen seed changed.'}
$seed=((Get-Content -LiteralPath $seedPath -Encoding utf8 | Where-Object {$_ -match '^>'} | ForEach-Object {$_ -replace '^> ?',''}) -join "`n").Trim()
$control=@'
This is the controlled Stage2 brownfield BMAD experiment. Use the installed BMAD6.12.0 native skills/workflows, in English, headless using their documented modes. The complete shared seed below is unchanged. Work only in this Stage2/Bmad Method root; never read/copy another tool's app or specs. Preserve the inherited _bmad-output/planning-artifacts and implementation-artifacts byte-for-byte; new native output belongs in _bmad-output/stage2 per configured paths. Do not change Stage1, shared toolchain, Git branches/commits/push, credentials, automatic tool updates or tool package sources. Only you generate feature specifications and app/test/dependency changes; researcher helpers/evidence are labelled separately. Do not delegate: use the documented sequential fallback and record the headless no-delegation/fast-path override in native memlogs. Preserve required native steps; skip unrelated market research, optional brainstorming and repeated whole-source ingestion. Read only relevant files/current workflow step, reuse on-disk progress, avoid dumping complete large reports. Do not fabricate timestamps/durations or test success; raw command results are authoritative. Return concise artifact paths, actual checks and unresolved limits; never just a next-step plan. Runtime maxSessionTurns80 limits each invocation; incomplete work stays pending and may be continued, not claimed complete. No toolchain upgrade or intentional model switch.
'@
$request="$control`n`n$Instructions`n`nCommon seed (unchanged):`n$seed"
foreach ($suffix in @('prompt.txt','started.json','run.json','stdout.json','stderr.txt')) {if(Test-Path -LiteralPath (Join-Path $docs "$Label.$suffix")){throw 'Invocation label already exists.'}}
$prompt=Join-Path $docs "$Label.prompt.txt"
[IO.File]::WriteAllText($prompt,$request,[Text.UTF8Encoding]::new($false))
$env:GOOGLE_GENAI_USE_VERTEXAI='true';$env:GOOGLE_CLOUD_PROJECT='project-d419b4aa-7c3b-4fde-932';$env:GOOGLE_CLOUD_LOCATION='global';$env:GEMINI_MODEL='gemini-3.5-flash'
$env:CLOUDSDK_CONFIG=Join-Path $env:APPDATA 'gcloud-tetris-last-mile'
$env:GOOGLE_APPLICATION_CREDENTIALS=Join-Path $env:CLOUDSDK_CONFIG 'application_default_credentials.json'
$credentialMetadata=Get-Content -LiteralPath $env:GOOGLE_APPLICATION_CREDENTIALS -Raw | ConvertFrom-Json
if ($credentialMetadata.quota_project_id -ne $env:GOOGLE_CLOUD_PROJECT) {throw 'Wrong authorized quota project.'}
Remove-Variable credentialMetadata
$env:GEMINI_CLI_TRUST_WORKSPACE='true';$env:GEMINI_CLI_HOME=Join-Path $docs 'gemini-home';$env:PYTHONDONTWRITEBYTECODE='1'
$env:UV_CACHE_DIR=Join-Path $docs 'uv-cache';$env:UV_PYTHON_DOWNLOADS='never'
$env:PATH=(Join-Path $toolRoot 'backend/.venv/Scripts')+';'+(Join-Path $caseRoot 'Etapa 1/_toolchain/venv/Scripts')+';'+(Join-Path $caseRoot 'Etapa 1/_toolchain/node_modules/.bin')+';'+$env:PATH
$manifest=Get-Content -LiteralPath (Join-Path $toolRoot '_bmad/_config/manifest.yaml') -Raw
if ($manifest -notmatch 'version: 6\.12\.0') {throw 'Unexpected BMAD version.'}
$stdout=Join-Path $docs "$Label.stdout.json";$stderr=Join-Path $docs "$Label.stderr.txt"
$start=Get-Date
$record=[ordered]@{label=$Label;category=$Category;qa_intent_id=$QaIntent;started=$start.ToString('o');requested_model='gemini-3.5-flash';gemini_cli_version='0.60.0';bmad_version='6.12.0';project=$env:GOOGLE_CLOUD_PROJECT;location='global';credential_profile='gcloud-tetris-last-mile (outside workspace)';max_session_turns=80;submission_method='complete multiline plain prompt via direct Node entrypoint';prompt_sha256=(Get-FileHash -LiteralPath $prompt).Hash;seed_sha256=(Get-FileHash -LiteralPath $seedPath).Hash;launcher_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash;settings_sha256=(Get-FileHash -LiteralPath (Join-Path $toolRoot '.gemini/settings.json')).Hash}
$record|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $docs "$Label.started.json") -Encoding utf8
$entry=Join-Path $caseRoot 'Etapa 1/_toolchain/node_modules/@google/gemini-cli/bundle/gemini.js'
& 'C:/Program Files/nodejs/node.exe' $entry -m gemini-3.5-flash --approval-mode yolo --output-format json -p $request 1> $stdout 2> $stderr
$code=$LASTEXITCODE;$end=Get-Date
$record['ended']=$end.ToString('o');$record['duration_seconds']=[Math]::Round(($end-$start).TotalSeconds,3);$record['exit_code']=$code;$record['stdout']=$stdout;$record['stderr']=$stderr
$record|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $docs "$Label.run.json") -Encoding utf8
Write-Output ($record|ConvertTo-Json -Depth 8 -Compress)
exit $code
