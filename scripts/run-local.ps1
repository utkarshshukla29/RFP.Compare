$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

& $venvPython -m streamlit run (Join-Path $projectRoot "app.py") --server.address 127.0.0.1 --server.port 8501
exit $LASTEXITCODE