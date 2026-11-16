# Script de inventario SHA-256 para la preparacion de la Etapa 2 (Kiro).
# Recorre un arbol aplicando las mismas reglas de exclusion usadas en la copia,
# y produce un CSV con: RelativePath, SizeBytes, SHA256.

param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$OutCsv
)

$excludedDirs = @('node_modules', '.venv', 'venv', '__pycache__', '.pytest_cache', 'dist', '.git')
$excludedExt  = @('.pyc')
$excludedNames = @('shift_bank.db', 'shift_bank.db-journal', 'shift_bank.db-wal', 'shift_bank.db-shm', '.env')

$rootFull = (Resolve-Path $Root).Path
$rows = New-Object System.Collections.Generic.List[object]

Get-ChildItem -Force -Recurse -File $rootFull | ForEach-Object {
    $rel = $_.FullName.Substring($rootFull.Length).TrimStart('\')
    $parts = $rel -split '\\'
    $skip = $false
    foreach ($p in $parts[0..($parts.Length - 2)]) { if ($excludedDirs -contains $p) { $skip = $true; break } }
    if (-not $skip) {
        if ($excludedExt -contains $_.Extension.ToLower()) { $skip = $true }
        if ($excludedNames -contains $_.Name) { $skip = $true }
        if ($_.Name -like '*.log') { $skip = $true }
    }
    if (-not $skip) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash
        $rows.Add([pscustomobject]@{
            RelativePath = ($rel -replace '\\', '/')
            SizeBytes    = $_.Length
            SHA256       = $hash
        })
    }
}

$rows = $rows | Sort-Object RelativePath
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $OutCsv
Write-Output "Inventariados $($rows.Count) archivos -> $OutCsv"
