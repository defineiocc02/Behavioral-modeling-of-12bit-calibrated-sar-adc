# Exploratory analyses

This directory preserves parameter sweeps and historical comparison plots.
They are not release evidence and must not override the current configuration
or the frozen matrix under `evidence/mismatch_matrix/`.

In particular, plots involving 512 pairs, 1 mV calibration noise, enabled
dither, flat PER-CAP stress, or very large mismatch were architecture studies.
The v3.1 acceptance path is:

- PER-UNIT mismatch;
- 128 calibration pairs;
- recursive Q8 target commits;
- no extra dither DAC;
- 0 mV mismatch-isolation runs and 0.3 mV RMS calibration-only stability runs;
- zero noise during normal conversion.

Use `scripts/run_mismatch_matrix.ps1` for formal regeneration.
