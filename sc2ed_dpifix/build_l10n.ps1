$ErrorActionPreference = 'Stop'

$Compiler = 'E:\msys2\ucrt64\bin\g++.exe'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$L10n = Join-Path $Here 'l10n'
$HookPackage = Join-Path $Here 'packages\hook'

if (-not (Test-Path -LiteralPath $Compiler)) {
    throw "C++ compiler not found: $Compiler"
}

& $Compiler -std=c++17 -O2 -Wall -Wextra -Wpedantic -shared -static `
    (Join-Path $L10n 'hook.cpp') `
    -o (Join-Path $HookPackage 'SC2EditorDependencyL10n.dll')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Get-Item (Join-Path $HookPackage 'SC2EditorDependencyL10n.dll'), `
    (Join-Path $HookPackage 'OfficialDependencyNames.tsv'), `
    (Join-Path $HookPackage 'OfficialResourceNames.tsv') |
    Select-Object FullName, Length, LastWriteTime
