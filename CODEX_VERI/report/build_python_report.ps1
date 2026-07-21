$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $ProjectRoot 'tmp\latex\python_stage'
$OutputDir = Join-Path $ProjectRoot 'output\pdf'
$TexFile = Join-Path $PSScriptRoot 'python_stage_report_cn.tex'
$FinalPdf = Join-Path $OutputDir 'CODEX_VERI_Python_Calibration_Verification_Report.pdf'

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Push-Location $PSScriptRoot
try {
    $OutputArg = "-output-directory=$BuildDir"
    & xelatex -interaction=nonstopmode -halt-on-error -file-line-error $OutputArg $TexFile
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass 1 failed with exit code $LASTEXITCODE" }
    & xelatex -interaction=nonstopmode -halt-on-error -file-line-error $OutputArg $TexFile
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass 2 failed with exit code $LASTEXITCODE" }
    Copy-Item -Force -LiteralPath (Join-Path $BuildDir 'python_stage_report_cn.pdf') -Destination $FinalPdf
} finally {
    Pop-Location
}

Write-Output $FinalPdf
