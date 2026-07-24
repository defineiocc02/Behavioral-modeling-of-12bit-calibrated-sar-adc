param(
    [switch]$RunPipeline,
    [ValidateRange(1, 1000)]
    [int]$Seeds = 8
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot

try {
    $env:PYTHONPATH = Join-Path $repoRoot "src"

    Write-Host "[1/3] Running Python regression tests"
    python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }

    Write-Host "[2/3] Regenerating documentation figures"
    python docs\figures\generate_modeling_figures.py
    if ($LASTEXITCODE -ne 0) {
        throw "figure generation failed with exit code $LASTEXITCODE"
    }

    if ($RunPipeline) {
        Write-Host "[3/3] Running dynamic calibration pipeline with $Seeds seeds"
        $env:SAR_MC_SEEDS = "$Seeds"
        python src\python_cal\run_final_calibration_pipeline.py
        if ($LASTEXITCODE -ne 0) {
            throw "calibration pipeline failed with exit code $LASTEXITCODE"
        }
    }
    else {
        Write-Host "[3/3] Pipeline skipped; pass -RunPipeline to execute it"
    }

    Write-Host "Reproduction completed."
}
finally {
    Pop-Location
}
