param(
    [int]$Seeds = 100,
    [int]$AveragePairs = 128,
    [int]$SeedStart = 10000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$srcRoot = Join-Path $repoRoot "src"
$pipeline = Join-Path $srcRoot "python_cal\run_final_calibration_pipeline.py"
$matrixRoot = Join-Path $srcRoot "python_cal\validation_results\mismatch_matrix"
$statusPath = Join-Path $matrixRoot "matrix_status.json"

if (($AveragePairs -band ($AveragePairs - 1)) -ne 0) {
    throw "AveragePairs must be a power of two for RTL-equivalent averaging"
}

$cases = @(
    @{
        Label = "ideal_zero_noise"
        Sigma = "0"
        CalNoise = "0"
        Seeds = 1
        Purpose = "deterministic ideal baseline"
    },
    @{
        Label = "mismatch_0p5_zero_noise"
        Sigma = "0.005"
        CalNoise = "0"
        Seeds = $Seeds
        Purpose = "nominal mismatch, isolate calibration from noise"
    },
    @{
        Label = "mismatch_0p5_calnoise_0p3mV"
        Sigma = "0.005"
        CalNoise = "0.0003"
        Seeds = $Seeds
        Purpose = "nominal mismatch with quantization-lock release"
    },
    @{
        Label = "mismatch_1p0_zero_noise"
        Sigma = "0.01"
        CalNoise = "0"
        Seeds = $Seeds
        Purpose = "conservative mismatch stress, zero calibration noise"
    },
    @{
        Label = "mismatch_1p0_calnoise_0p3mV"
        Sigma = "0.01"
        CalNoise = "0.0003"
        Seeds = $Seeds
        Purpose = "secondary calibration-noise robustness check"
    }
)

New-Item -ItemType Directory -Force -Path $matrixRoot | Out-Null
$env:PYTHONPATH = $srcRoot
$env:SAR_AVG_PAIRS = [string]$AveragePairs
$env:SAR_SEED_START = [string]$SeedStart

$completed = @()
foreach ($case in $cases) {
    $label = $case.Label
    $env:SAR_MC_SIGMA = $case.Sigma
    $env:SAR_CAL_NOISE_SIGMA_V = $case.CalNoise
    $env:SAR_MC_SEEDS = [string]$case.Seeds
    $env:SAR_OUT_DIR = Join-Path $matrixRoot $label

    Write-Output (
        "START {0}: sigma={1}, cal_noise={2}, seeds={3}, pairs={4}" -f
        $label, $case.Sigma, $case.CalNoise, $case.Seeds, $AveragePairs
    )
    & python $pipeline
    if ($LASTEXITCODE -ne 0) {
        throw "Pipeline failed for $label with exit code $LASTEXITCODE"
    }
    $completed += $label
    @{
        state = "running"
        completed = $completed
        current = $label
        seeds = $case.Seeds
        mismatch_seeds = $Seeds
        average_pairs = $AveragePairs
        seed_start = $SeedStart
        updated_utc = [DateTime]::UtcNow.ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $statusPath
}

@{
    state = "complete"
    completed = $completed
    mismatch_seeds = $Seeds
    average_pairs = $AveragePairs
    seed_start = $SeedStart
    updated_utc = [DateTime]::UtcNow.ToString("o")
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $statusPath

Write-Output "MISMATCH MATRIX COMPLETE"
