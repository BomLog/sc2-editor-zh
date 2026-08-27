$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Work = Split-Path -Parent $Here
$Python = Join-Path $Work '.venv\Scripts\python.exe'

Push-Location $Work
try {
    & $Python (Join-Path $Here 'generate_official_dependency_names.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

& (Join-Path $Here 'build_l10n.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location $Here
try {
    & $Python -m PyInstaller --noconfirm --clean SC2DPIFix.spec
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
