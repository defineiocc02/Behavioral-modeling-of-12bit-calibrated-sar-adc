# Bridge CDAC SNDR Root Cause Report

## Verdict: **MODELING_BUG**

Decoder mapping was the primary root cause of 50% missing codes. With corrected decoder (divide signed_sum by 2), full 4096-code coverage achieved. SNDR (73.6 dB) matches ideal 12-bit quantizer (73.6 dB) within 0.0 dB — parity lock is not a physical limitation, it was a decoder mapping error. Half-grid sparsity (L1C=2 Q0 without physical terminal) exists as a secondary architecture property but does not prevent full 12-bit resolution in this ideal model.

## Key Metrics

| Metric | Value |
| --- | --- |
| Ideal quantizer SNDR | 73.6 dB |
| Bridge SAR nominal SNDR | 73.6 dB |
| Codebook (exhaustive) SNDR | 67.1 dB |
| Flat CDAC SNDR | 73.6 dB |
| Physical VDIFF levels | 4160/8192 |
| Min VDIFF gap | 4.199720e-04 V |
| Code LSB (2*VFS/4096) | 4.197671e-04 V |
| DAC step / code LSB | 2.0 Q0 = 1.0 code-LSB |
| Grid bin gaps (1 LSB) | 65/4096 |
| DC sweep missing codes (nominal) | 0/4096 |
| DC sweep missing codes (physical) | 0/4096 |

## Evidence

1. Parity lock: 3 odd-valued weights (stages [5, 6, 13]: [65, 65, 1]). In ideal integer-weight zero-noise CDAC, signed_sum = Σ(1-2d_i)*w_i is always odd, producing code step = 1 (after correct decoder divide-by-2). With correct decoder (÷2), integer Q0 weights do NOT cause systematic missing codes. In real circuits, capacitor mismatch causes transition-level shifts (DNL/INL), not the 50% parity-locked code loss seen with the old decoder.
2. Half-grid sparsity: L1C physical capacitor weight = 2 Q0, terminal (1 Q0) has NO physical capacitor. However, terminal comparator decision (stage 13, decoder weight=1) fills the 2-Q0 gap during normal SAR conversion, achieving effective 1-LSB resolution. Measured SNDR = 73.6 dB = ideal 12-bit, confirming the terminal comparison resolves the half-grid sparsity in practice.
3. DC sweep: 0/4096 missing codes. Full 4096-code coverage achieved with corrected decoder. Non-monotonic: nominal=0, physical=0.
4. Bridge SAR SNDR: nominal=73.6 dB (ENOB=11.93), ideal quantizer=73.6 dB, gap=0.0 dB. SNDR matches ideal 12-bit quantizer — no bridge penalty.
5. Codebook exhaustive: 67.1 dB vs fixed-order SAR: 73.6 dB. SAR search near-optimal.
6. Flat CDAC: 73.6 dB vs bridge: 73.6 dB. Bridge not the bottleneck (flat≈bridge).

## Counter-experiments

- Experiment A: codebook search separates SAR strategy from DAC physics
- Experiment B: flat CDAC removes bridge from equation
- Experiment C: decoder attribution (nominal vs physical vs calibrated)
- Experiment D: H1C-A sensitivity to 65/64 asymmetry
- Experiment E: bridge cap sweep tests topology sensitivity

## Bridge Capacitor Sweep

**Note:** 'Missing DC Codes' column is INVALID — the DC sweep used only 1025 input points (4096−1025≈3071 codes unobserved regardless of architecture). A proper sweep requires ≥65537 points. See document 40 D6.

| CB Multiplier | CB (Cu) | SNDR (dB) | SFDR (dB) |
| --- | --- | --- | --- |
| 0.950 | 1.9000 | 62.7 | 76.9 |
| 0.975 | 1.9500 | 68.1 | 83.7 |
| 1.000 | 2.0000 | 73.6 | 95.2 |
| 1.025 | 2.0500 | 68.4 | 83.0 |
| 1.050 | 2.1000 | 63.7 | 77.8 |

## Generated Files

- dc_sweep_raw.csv
- reachable_levels.csv
- single_cap_steps.csv
- fft_spectrum_ideal_quantizer.csv
- fft_spectrum_bridge_sar.csv
- conversion_trace_zero.csv
- conversion_trace_boundary.csv
