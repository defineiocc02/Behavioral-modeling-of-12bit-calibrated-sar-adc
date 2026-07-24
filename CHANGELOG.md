# Changelog

All notable changes to the public Python behavioral model are recorded here.

## 3.0.0 — 2026-07-25

### Architecture

- Replaced the retired 128-Cu single-redundancy array with the locked integer
  `71 Cu high / 2 Cu bridge / 65 Cu low` topology (138 Cu per side).
- Added duplicate 8-Cu high and duplicate 2-Cu low branches.
- Connected all fourteen high/low capacitors to VIN during normal sampling.
- Increased normal conversion from fourteen to fifteen comparisons (+1).

### Calibration and decode

- Uses the full 131-Q0 low segment as the matched calibration ruler.
- Calibrates H1, H2, H4, H8-R, H8-A, H16 and H32 with the existing
  force-0/force-1 half-difference method.
- Keeps 512 pairs and 14336 calibration sub-conversions, equal to v2.1.
- Removed the unused centroid LUT decoder; active decode is only a P/N
  weighted sum with Q2 rounding.

### Verification and documentation

- Passes 63/63 active Python regression tests.
- Passes the 100/100-seed release pipeline: calibrated SNDR/ENOB P50
  `74.482 dB / 12.080 bit`, oracle-gap P50/P95 `0.156/0.412 dB`,
  zero missing codes, DNL/INL peak P95 `0.8663/0.9234 LSB`.
- Retains 27065 formal local integer backsteps as a diagnostic limitation;
  no LUT, sorting or remapping is used to conceal them.
- Added exact code-density DNL/INL alongside the stronger formal local
  backstep diagnostic.
- Locked coherent FFT to N=4096, k=127, phase=0.123, -0.5 dBFS, dynamic VFS
  and a rectangular window.
- Replaced stale documentation and figures with v3.0 sources and generated
  evidence.
- Removed old active-tree Verilog-A, RTL, Spectre, report and review copies;
  Git history and release tags remain the archive.

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
