# SAR ADC Calibration Pipeline — Final Validation Report

**Run ID:** `a3330136`
**Date:** 0
**Mode:** 7-Target Shen half-difference + fixed dither + Q2 output
**MC Seeds:** 100, unit-cap sigma=0.5%
**Calibration:** 512 avg pairs, cal_noise=0.001 V
**Static test:** sampled every 64 codes (64 sample points)

## Summary

| Metric | Value |
|--------|-------|
| Valid calibrations | 100/100 |
| Oracle gap P50 | 0.222 dB |
| Oracle gap P95 | 0.524 dB |
| Gap <= 0.5 dB | 94/100 (94%) |
| Gap <= 1.0 dB | 99/100 (99%) |
| SNDR cal P50 | 73.11 dB |
| ENOB cal P50 | 11.85 bit |
| Negative gain | 0/100 (0.0%) |
| DNL peak P95 | 0.0226 LSB |
| INL peak P95 | 1.7353 LSB |
| Total missing codes | 0 |
| Elapsed | 1288s |

## Verdict

**Oracle-gap diagnostic: PASS** (gap P50 = 0.222 dB, P95 = 0.524 dB)
**Absolute dynamic gate: PASS** (all calibrated ENOB > 11.5 bit and SNDR > 70.99 dB)
**Static: CONDITIONAL (full=0/100; sampled remainder)**
**Top-level acceptance: FAIL**

## Per-Target Weight Errors (Absolute Q0)

| Target | P50 (Q0) | P95 (Q0) | Mean (Q0) |
|--------|:---:|:---:|:---:|
| H1C-R | 0.1797 | 0.3765 | 0.1947 |
| H1C-A | 0.1783 | 0.4271 | 0.2001 |
| H2C | 0.2663 | 0.7726 | 0.3157 |
| H4C | 0.4960 | 1.4442 | 0.6001 |
| H8C | 0.8672 | 2.8114 | 1.1049 |
| H16C | 1.7687 | 5.5258 | 2.1388 |
| H32C | 3.2743 | 10.8503 | 4.1875 |

## Per-Target Normalized Ratio Errors |e_ratio|

e_ratio = (Ŵ_i/ΣŴ) / (W_i/ΣW) - 1, removes global scale factor.

| Target | P50 | P95 | Mean |
|--------|:---:|:---:|:---:|
| H1C-R | 0.001105 | 0.002550 | 0.001158 |
| H1C-A | 0.000968 | 0.002922 | 0.001133 |
| H2C | 0.000417 | 0.001264 | 0.000524 |
| H4C | 0.000210 | 0.000701 | 0.000296 |
| H8C | 0.000147 | 0.000376 | 0.000160 |
| H16C | 0.000074 | 0.000234 | 0.000095 |
| H32C | 0.000065 | 0.000177 | 0.000076 |

## Method

- **Calibration:** Shen 2018 force-0/force-1 protocol, P/N split-side
- **Targets:** 7 stages (H1R, H1A, H2C, H4C, H8C, H16C, H32C high-segment recursive)
- **Base ruler:** Low segment L32C..T1C (nominal weights, 127 Q0 total)
- **Calibration order:** H1R->H1A->H2C->H4C->H8C->H16C->H32C
- **Decoder:** Uses calibrated weights for all 14 stages
- **Static test:** sampled every 64 codes (64 points)
- **FFT:** 4096-point, rectangular window (coherent sampling), bin k=127

## Known Limitations

- **Low-segment nominal weights:** L32C..T1C use nominal weights as the base ruler.
  Low-segment shape error contributes ~0.2 dB to the SNDR gap through H1R calibration error.
- **Bridge attribution:** Not assigned from this run. Bridge-only and high-only
  mismatch must be separated by A/B experiments; a pure common gain error is not
  sufficient evidence for an SNDR loss.
- **Recursive noise accumulation:** Noise propagates through the 7-stage calibration chain.
  512 avg pairs (~0.033 LSB per measurement) provides sufficient statistical suppression.
- **Strict binary weighting:** Low-segment bit-by-bit calibration is mathematically impossible
  because sum(lower) = target - 1 in binary-weighted arrays. The low segment cannot be
  self-calibrated using the Shen force-0/force-1 protocol.
