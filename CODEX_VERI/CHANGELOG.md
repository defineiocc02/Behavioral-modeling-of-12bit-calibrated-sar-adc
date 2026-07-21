# CODEX_VERI change log

## 0.3.0 - 2026-07-22

- Added an independent split-CDAC physical model and a separate calibrated decoder.
- Added coherent two-tone FFT/least-squares cross-checks, clipping guards, static ramps, and 2000 physical Monte Carlo samples (4000 dynamic records).
- Exposed the current 12-bit integer decoder limitation: 19/4000 records pass ENOB > 11.5 even with 128 calibration pairs.
- Accepted the minimum digital-precision candidate: 128-pair Q2 reconstruction passes 4000/4000, with minimum ENOB 11.5213 bit and 95% one-sided yield lower bound 99.925%.
- Quantified hardware cost: Q2 adds two retained fractional output bits and no normal-conversion cycle or CDAC branch; 128 pairs increase foreground calibration time from 67.2 us to 268.8 us.
- Rejected 512/1024-pair averaging and large context LUTs as primary solutions on startup-time/memory cost.
- Reviewed Wang et al. (2022) self-measurement: useful as a future fast measurement front-end, but it does not remove weighted-output fractional precision or final requantization requirements.
- Preserved the static caveat: selected worst Q2 ramps contain small -0.25 to -0.5 LSB backsteps, so dynamic ENOB acceptance is not a full INL/DNL sign-off.

## 0.2.0 - 2026-07-22

- Independent adversarial review initially rejected the Python gate with six P1 findings.
- Enforced unique and complete 7-target by 32-pair log coverage.
- Cross-checked logged `DIFF` against `DPLUS-DMINUS` within the declared three-decimal print tolerance.
- Bound the gate result to 25 unit tests, complete experiment configuration, and SHA-256 hashes of generating code, tests, report source, and manifests.
- Checked all seven observed target means separately from the H1C-R-seeded causal propagation model.
- Added a 127 LSB candidate residual-reach guard with explicit saturation failure.
- Replaced a weak RMSE comparison with a maximum RMSE-ratio gate and paired MSE-improvement 95% confidence interval.
- Added absolute noise-bias and N=32/N=1 standard-deviation-ratio limits in addition to slope and family-wise interval checks.
- All changes remain confined to `CODEX_VERI/`.

## 0.1.0 - 2026-07-22

- Created an isolated Python-first calibration verification project.
- Registered immutable hashes for the initial Verilog-A, testbench, paper, reports, and Spectre evidence.
- Added exact signed-quantizer, empirical-log replay, recursive calibration, and statistical experiment scaffolding.
- No file outside `CODEX_VERI/` was modified by this stage.
- Separated Huang's paper equations, historical legacy replay, and the project
  wall-plus-signed candidate after independent review found a provenance risk.
- Added explicit saturation and offset-drift tests; neither behavior is hidden by clipping.
- Added an XeLaTeX/ctex academic report source and build script per user requirement.
