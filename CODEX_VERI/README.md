# CODEX_VERI

This directory is an isolated Python-first verification project for the Huang-style
recursive SAR ADC weight-calibration algorithm.

## Hard gate

1. Python mathematical contract and tests must pass completely.
2. Python experiments must reproduce the observed legacy bias and demonstrate the
   properties of the candidate signed-centered estimator.
3. An independent review must close all Python-stage findings.
4. Only then may a later stage compare Verilog-A decisions against frozen Python vectors.

Files outside this directory are read-only evidence. Their paths and SHA-256 hashes
are recorded in `evidence/source_manifest.json`.

## Reproduce

Run from PowerShell:

```powershell
.\CODEX_VERI\run_python_gate.ps1
```

All caches, intermediate files, figures, tables, and reports are kept below this
directory.
