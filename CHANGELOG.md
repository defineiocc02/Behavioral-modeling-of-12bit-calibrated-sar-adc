# Changelog

All notable changes to the public Python behavioral model are recorded here.

## 2.1.0 — 2026-07-24

### Added

- Added a repository-level README with model scope, quantitative results,
  reproduction steps, code map and explicit claim boundaries.
- Added 11 reproducible publication-quality figure sets in PNG, SVG and PDF.
- Added `docs/MODELING_GUIDE.md`, `docs/VALIDATION_STATUS.md` and
  `docs/FIGURE_CATALOG.md`.
- Added `pyproject.toml`, behavioral `spec.yml`, reproducibility PowerShell
  entry point and GitHub Actions test/figure workflow.
- Added a root version file and iteration log.
- Added a point-by-point external calibration review response.
- Added a dedicated active `shen_switching.py` module and Shen-specific state
  vocabulary.

### Changed

- Updated `python_cal.__version__` from 2.0.0 to 2.1.0.
- Isolated the deprecated calDAC controller behind a lazy compatibility import.
- Added regression gates that prevent the frozen observable-alpha experiment
  and legacy switching helpers from re-entering the active Shen path.
- Made the GitHub-facing status explicit: dynamic calibration passes, strict
  full-static monotonicity fails, and paper-exact Shen remains unimplemented.
- Documented Q2 as the minimum output precision that retains calibrated
  fractional weights without changing physical ADC conversion cycles.

### Verified

- 60/60 tests pass from a clean staged index.
- 100/100 dynamic Monte Carlo calibrations are valid.
- Calibrated SNDR/ENOB P50 = 73.112 dB / 11.852 bit.
- All generated PDFs have embedded fonts and zero Type 3 fonts.

## 2.0.0 — 2026-07-24

- Replaced the physical terminal capacitor assumption with a comparator-only
  terminal decision.
- Added P/N independent physical weights and decoding.
- Corrected Shen-derived VREFN/VREFP half-difference weight measurement.
- Added fixed symmetric dither and corrected calibration offset units.
- Added float/Q2 decoding and retained integer decoding as a diagnostic.
- Unified coherent FFT/VFS/clipping protocol and corrected SFDR harmonic masks.
- Added full-static and carry-margin audits.
- Established the root-cause conclusion that integer re-quantization, not
  input amplitude or ideal CDAC ceiling, caused the apparent 11-bit result.
