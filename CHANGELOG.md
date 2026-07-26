# Changelog

All notable changes to the public Python behavioral model are recorded here.

## 3.1.1 — 2026-07-26

### VM evidence and workspace governance

- Froze the compact standalone Spectre/Xcelium evidence package, including
  source hashes, task-owned testbenches, runner, status, protected-path audit,
  and deterministic manifest generation.
- Verified both Verilog-A modules in an isolated VM sandbox: the comparator
  completed with zero warnings, while the CDAC completed with four retained
  `VACOMP-1116` continuous-signal `transition()` warnings.
- Re-ran the calibration and lower-SAR RTL self-checks with Xcelium and
  compile/elaborated `cal_top`; all five standalone sandbox gates passed.
- Added a VM remote-operations and space-governance standard and reorganized
  local/VM generated artifacts without touching the active Cadence project.
- Updated the academic report and claim boundary from "VA source review only"
  to "standalone smoke passed; full-ADC AMS remains open."

## 3.1.0 — 2026-07-26

### Mismatch-focused verification

- Added a five-case formal matrix: ideal, 0.5% and 1.0% PER-UNIT mismatch,
  each with zero calibration disturbance and, for mismatch cases, a 0.3 mV
  RMS calibration-comparator stability condition.
- Kept normal conversion noise at zero and separated calibration measurement
  decorrelation from ADC noise performance.
- Corrected the pre/post comparison to Q2-to-Q2 and retained integer-12 only
  as a diagnostic.
- Added frozen CSV/JSON/manifests, SHA-256 aggregation and report generation
  directly from the frozen evidence.

### Python/RTL/Verilog-A alignment

- Truncates every recursive Python target update to Q8, exactly matching the
  synthesizable RTL register and arithmetic-shift behavior.
- Reworked the calibration FSM and lower-SAR RTL around signed Q8 sums,
  per-side recursive P/N weights, complete pair accumulation and explicit
  failure status.
- Added self-checking XSIM coverage for the seven-target FSM and recursive
  lower-SAR ruler.
- Corrected the Verilog-A sampling model so only VTOP is clamped to VCM;
  VBRIDGE remains the internal floating split-array node.

### Overdesign removal and claim boundaries

- Uses 128 pairs instead of the retired 512-pair default.
- Removed duplicate/unused RTL CDAC and accumulator modules, the duplicate
  comparator Verilog-A model, and a stale contradictory synthesis report.
- Keeps the active decoder as an ordinary P/N weighted sum: no LUT, CAM,
  remap table, monotonic clamp, calibration sub-DAC or auxiliary comparator.
- Removed unsupported foundry/process claims; 4 fF and the 0.5%/1.0% mismatch
  points remain behavioral assumptions until replaced by target-PDK evidence.
- Replaced the release report with a mismatch-centered PDF and explicit
  transistor/PVT/post-layout signoff gaps.

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
