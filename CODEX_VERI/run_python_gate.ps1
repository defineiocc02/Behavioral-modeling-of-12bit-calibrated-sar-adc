$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent $ProjectRoot
$PythonExe = 'C:\Users\Administrator\miniconda3\python.exe'

$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = Join-Path $ProjectRoot 'tmp\pycache'
$env:MPLCONFIGDIR = Join-Path $ProjectRoot 'tmp\matplotlib'

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'tmp') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'results\raw') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'results\tables') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'results\figures') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'output\pdf') | Out-Null

Push-Location $ProjectRoot
try {
    & $PythonExe experiments\run_python_verification.py
    if ($LASTEXITCODE -ne 0) { throw "Python unit-test/verification gate failed with exit code $LASTEXITCODE" }
    & $PythonExe experiments\run_adc_performance_verification.py
    if ($LASTEXITCODE -ne 0) { throw "ADC performance gate failed with exit code $LASTEXITCODE" }
    & $PythonExe figures\generate_figures.py
    if ($LASTEXITCODE -ne 0) { throw "Figure generation failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
