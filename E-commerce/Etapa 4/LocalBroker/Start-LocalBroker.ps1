$ErrorActionPreference = 'Stop'
$provision = Join-Path $PSScriptRoot 'provision.sh'
$relay = Join-Path $PSScriptRoot 'amqp_forwarder.py'
$pidFile = Join-Path $PSScriptRoot 'forwarder.pid'
$outLog = Join-Path $PSScriptRoot 'forwarder.out.log'
$errLog = Join-Path $PSScriptRoot 'forwarder.err.log'
$python = (Get-Command python -ErrorAction Stop).Source
function Test-Amqp([string]$Address) {
    & $python $relay --probe $Address 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}
$linuxPath = (& wsl -d Ubuntu -- wslpath -a $provision).Trim()
if ($LASTEXITCODE -ne 0 -or !$linuxPath) { throw 'No se pudo resolver la ruta de Ubuntu/WSL.' }
& wsl -d Ubuntu -u root -- bash $linuxPath
if ($LASTEXITCODE -ne 0) { throw 'RabbitMQ no pudo arrancar en Ubuntu/WSL.' }
# Verify actual IPv4 AMQP, not the existence of an unrelated/IPv6 listener.
if (Test-Amqp '127.0.0.1') {
    Write-Host 'RabbitMQ disponible y verificado por AMQP en 127.0.0.1:5672.'
    return
}
$addresses = (& wsl -d Ubuntu -- hostname -I) -join ' '
if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener la direccion de Ubuntu/WSL.' }
$upstream = ($addresses -split '\s+' | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } | Select-Object -First 1)
if (!$upstream) { throw 'Ubuntu/WSL no devolvio una direccion IPv4.' }
if (!(Test-Amqp $upstream)) {
    throw ("Windows no recibe AMQP de {0}:5672 aunque RabbitMQ arranco en WSL. Comprueba la conectividad Windows/WSL." -f $upstream)
}
# Replace only our recorded stale relay, never an arbitrary port owner.
if (Test-Path $pidFile) {
    $oldPid = 0
    if ([int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$oldPid)) {
        $oldProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$oldPid" -ErrorAction SilentlyContinue
        if ($oldProcess -and $oldProcess.CommandLine -and $oldProcess.CommandLine.Contains($relay)) {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
        }
    }
}
$arguments = '"' + $relay + '" --upstream "' + $upstream + '"'
$startOptions = @{
    FilePath=$python; ArgumentList=$arguments; WindowStyle='Hidden'; PassThru=$true
    WorkingDirectory=$PSScriptRoot; RedirectStandardOutput=$outLog; RedirectStandardError=$errLog
}
$proc = Start-Process @startOptions
$proc.Id | Set-Content $pidFile
Write-Host ("Preparando puente Windows -> RabbitMQ {0}:5672..." -f $upstream)
$timer = [Diagnostics.Stopwatch]::StartNew()
while ($timer.Elapsed.TotalSeconds -lt 30) {
    if (Test-Amqp '127.0.0.1') {
        Write-Host 'RabbitMQ disponible y verificado por AMQP en 127.0.0.1:5672.'
        return
    }
    $proc.Refresh()
    if ($proc.HasExited) { break }
    Start-Sleep -Milliseconds 300
}
$details = if (Test-Path $errLog) { (Get-Content $errLog -Tail 8) -join [Environment]::NewLine } else { 'Sin registro de errores.' }
if (!$proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
throw "El puente local no respondio por AMQP. Registro: $errLog. $details"
