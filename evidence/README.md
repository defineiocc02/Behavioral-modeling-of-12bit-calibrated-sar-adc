# Frozen validation evidence

`mismatch_matrix/` contains the selected machine-readable evidence used by
`docs/final_report.pdf`.

The source pipeline writes working results under the gitignored
`src/python_cal/validation_results/` tree.  After a matrix completes, only the
latest CSV, final summary, and run manifest for each declared case are copied
here.  `mismatch_matrix_summary.json` records SHA-256 digests for the selected
CSV and summary files as well as the Python pipeline and acceptance sources.

Regenerate the aggregate and figures with:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m python_cal.validation.summarize_mismatch_matrix `
  --root evidence/mismatch_matrix
python scripts/generate_report_figures.py `
  --matrix-root evidence/mismatch_matrix
python scripts/generate_report_metrics.py
```

Evidence limitations are part of the data contract:

- behavioral Python L2 only;
- PER-UNIT mismatch: independent unit cells summed into each physical group;
- recursive calibration commits each target on the RTL-equivalent Q8 lattice;
- no normal-conversion noise injection;
- 0.3 mV RMS, where present, affects calibration measurements only;
- no transistor/PVT/post-layout or silicon claim.

This directory is the authority for behavioral mismatch statistics only.
Digital implementation evidence is kept separately in the self-checking
testbenches under `rtl/` and the tracked Vivado reports
`scripts/synth_util.rpt`, `scripts/synth_timing_summary.rpt`,
`scripts/synth_hold.rpt`, and `scripts/synth_check_timing.rpt`.
Local XSIM work directories remain gitignored because they contain tool
scratch data and machine-specific absolute paths.

`vm_sandbox/current_git_74e7366/` freezes the compact standalone Spectre and
Xcelium evidence package. It includes source hashes, task-owned testbenches,
the reproducible runner, status/evidence reports, and sanitized RTL logs. It
does not include raw PSF data, Xcelium caches, full Spectre logs, host IDs, or
license-server identifiers.
