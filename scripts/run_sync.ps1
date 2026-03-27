Param(
    [string]$ProjectRoot = $(Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$pythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$mainPy = Join-Path $ProjectRoot "main.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path $mainPy)) {
    throw "main.py not found: $mainPy"
}

Set-Location $ProjectRoot
& $pythonExe $mainPy
