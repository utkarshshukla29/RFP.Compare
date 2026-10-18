$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    py -3 -m venv --without-pip .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$systemPython = (py -3 -c "import sys; print(sys.executable)").Trim()
& $systemPython -m pip --python $venvPath install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $systemPython -m pip --python $venvPath install -r requirements.txt
exit $LASTEXITCODE