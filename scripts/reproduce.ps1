param(
    [switch]$RunPipeline,
    [switch]$RunMismatchMatrix,
    [switch]$BuildPdf,
    [ValidateRange(1, 1000)]
    [int]$Seeds = 100,
    [ValidateRange(2, 1024)]
    [int]$AveragePairs = 128,
    [ValidateRange(0.0, 0.2)]
    [double]$MismatchSigma = 0.005,
    [ValidateRange(0.0, 0.1)]
    [double]$CalibrationNoiseSigmaV = 0.0
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot

try {
    $env:PYTHONPATH = Join-Path $repoRoot "src"

    if ($RunPipeline -and $RunMismatchMatrix) {
        throw "Choose either -RunPipeline or -RunMismatchMatrix"
    }

    Write-Host "[1/4] Running Python regression tests"
    python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }

    if ($RunPipeline) {
        Write-Host "[2/4] Running calibration pipeline with $Seeds seeds"
        $env:SAR_MC_SEEDS = "$Seeds"
        $env:SAR_AVG_PAIRS = "$AveragePairs"
        $env:SAR_MC_SIGMA = "$MismatchSigma"
        $env:SAR_CAL_NOISE_SIGMA_V = "$CalibrationNoiseSigmaV"
        python src\python_cal\run_final_calibration_pipeline.py
        if ($LASTEXITCODE -ne 0) {
            throw "calibration pipeline failed with exit code $LASTEXITCODE"
        }
    }
    elseif ($RunMismatchMatrix) {
        Write-Host "[2/4] Running the formal mismatch matrix"
        & (Join-Path $PSScriptRoot "run_mismatch_matrix.ps1") `
          -Seeds $Seeds -AveragePairs $AveragePairs
        if ($LASTEXITCODE -ne 0) {
            throw "mismatch matrix failed with exit code $LASTEXITCODE"
        }

        python -m python_cal.validation.summarize_mismatch_matrix
        if ($LASTEXITCODE -ne 0) {
            throw "mismatch matrix aggregation failed"
        }
        python scripts\freeze_mismatch_evidence.py
        if ($LASTEXITCODE -ne 0) {
            throw "evidence freeze failed"
        }
        python -m python_cal.validation.summarize_mismatch_matrix `
          --root evidence\mismatch_matrix
        if ($LASTEXITCODE -ne 0) {
            throw "frozen evidence aggregation failed"
        }
    }
    else {
        Write-Host "[2/4] Simulation skipped; using committed evidence"
    }

    $matrixSummary = Join-Path $repoRoot `
      "evidence\mismatch_matrix\mismatch_matrix_summary.json"
    if (Test-Path $matrixSummary) {
        Write-Host "[3/4] Regenerating mismatch-report figures and metrics"
        python scripts\generate_report_figures.py `
          --matrix-root evidence\mismatch_matrix
        if ($LASTEXITCODE -ne 0) {
            throw "mismatch-report figure generation failed"
        }
        python scripts\generate_report_metrics.py
        if ($LASTEXITCODE -ne 0) {
            throw "report metric generation failed"
        }
        python scripts\generate_vm_evidence_manifest.py
        if ($LASTEXITCODE -ne 0) {
            throw "VM evidence manifest generation failed"
        }

        $figureDir = Join-Path $repoRoot "docs\figures\mismatch_report"
        $figureOutputs = Get-ChildItem -LiteralPath $figureDir -File
        if ($figureOutputs.Count -ne 21) {
            throw "expected 21 current figure files, found $($figureOutputs.Count)"
        }
        $figureTextFiles = @(
            (Join-Path $repoRoot "scripts\generate_report_figures.py")
        ) + @($figureOutputs | Where-Object { $_.Extension -eq ".svg" } |
            Select-Object -ExpandProperty FullName)
        $cjkHits = Select-String -Path $figureTextFiles `
          -Pattern "[\u3400-\u9FFF\uF900-\uFAFF]"
        if ($cjkHits) {
            throw "CJK text found inside current report figures"
        }
    }
    else {
        Write-Host "[3/4] Frozen matrix not present; report rendering skipped"
    }

    if ($BuildPdf) {
        Write-Host "[4/4] Building the PDF report with XeLaTeX"
        $previousSourceDateEpoch = $env:SOURCE_DATE_EPOCH
        $previousForceSourceDate = $env:FORCE_SOURCE_DATE
        # Freeze PDF creation metadata and trailer IDs to the v3.1.0
        # validation date so repeated builds remain byte-for-byte identical.
        $env:SOURCE_DATE_EPOCH = "1785024000"
        $env:FORCE_SOURCE_DATE = "1"
        Push-Location (Join-Path $repoRoot "docs")
        try {
            1..3 | ForEach-Object {
                xelatex -interaction=nonstopmode -halt-on-error final_report.tex
                if ($LASTEXITCODE -ne 0) {
                    throw "XeLaTeX pass $_ failed"
                }
            }
            $layoutWarnings = Select-String -Path "final_report.log" -Pattern `
              "Overfull|Undefined control sequence|LaTeX Warning: Label|Font Warning|fancyhdr Warning|Infinite glue"
            if ($layoutWarnings) {
                $layoutWarnings | ForEach-Object { Write-Host $_.Line }
                throw "PDF build contains blocking layout/reference/font warnings"
            }
        }
        finally {
            Pop-Location
            $env:SOURCE_DATE_EPOCH = $previousSourceDateEpoch
            $env:FORCE_SOURCE_DATE = $previousForceSourceDate
        }
    }
    else {
        Write-Host "[4/4] PDF build skipped; pass -BuildPdf to enable"
    }

    Write-Host "Reproduction completed."
}
finally {
    Pop-Location
}
