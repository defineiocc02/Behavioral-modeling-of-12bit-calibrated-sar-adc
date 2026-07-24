# SAR ADC Calibration Pipeline — Final Validation Report

**Run ID:** `dbac69f3`
**Date:** 20260724_173404
**Mode:** 7-target high-segment calibration + full-array sampling + Q2 weighted decoder + rectangular coherent FFT
**MC Seeds:** 100, unit-cap sigma=0.5%
**Calibration:** 512 avg pairs, cal_noise=0.001 V
**Static test:** exact reachable decision tree for every seed

## Summary

| Metric | Value |
|--------|-------|
| Valid calibrations | 100/100 |
| Oracle gap P50 | 0.156 dB |
| Oracle gap P95 | 0.412 dB |
| Gap <= 0.5 dB | 98/100 (98%) |
| Gap <= 1.0 dB | 100/100 (100%) |
| SNDR cal P50 (Q2) | 74.48 dB |
| SNDR cal P50 (integer 12b diagnostic) | 71.15 dB |
| ENOB cal P50 (Q2) | 12.08 bit |
| ENOB cal P50 (integer 12b diagnostic) | 11.53 bit |
| Negative gain | 0/100 (0.0%) |
| DNL peak P95 | 0.8663 LSB |
| INL peak P95 | 0.9234 LSB |
| Total missing codes | 0 |
| Formal sub-LSB integer backsteps (diagnostic) | 27065 |
| Elapsed | 1865s |

## Verdict

**Oracle-gap diagnostic: PASS** (gap P50 = 0.156 dB, P95 = 0.412 dB)
**Absolute dynamic gate: PASS** (all calibrated ENOB > 11.5 bit and SNDR > 70.99 dB)
**Static code-density: PASS; formal monotonic diagnostic: DIAGNOSTIC FAIL.**
**Top-level acceptance: PASS**

## Per-Target Weight Errors (Absolute Q0)

| Target | P50 (Q0) | P95 (Q0) | Mean (Q0) |
|--------|:---:|:---:|:---:|
| H1C | 0.1797 | 0.4788 | 0.2216 |
| H2C | 0.3014 | 0.8049 | 0.3586 |
| H4C | 0.5435 | 1.5343 | 0.6642 |
| H8C-R | 1.0448 | 3.0292 | 1.2466 |
| H8C-A | 1.0039 | 3.1613 | 1.2377 |
| H16C | 1.9804 | 6.2707 | 2.4338 |
| H32C | 3.8674 | 12.3308 | 4.7995 |

## Per-Target Normalized Ratio Errors |e_ratio|

e_ratio = (Ŵ_i/ΣŴ) / (W_i/ΣW) - 1, removes global scale factor.

| Target | P50 | P95 | Mean |
|--------|:---:|:---:|:---:|
| H1C | 0.000846 | 0.002554 | 0.001046 |
| H2C | 0.000486 | 0.001256 | 0.000530 |
| H4C | 0.000346 | 0.000790 | 0.000356 |
| H8C-R | 0.000125 | 0.000297 | 0.000135 |
| H8C-A | 0.000153 | 0.000353 | 0.000153 |
| H16C | 0.000067 | 0.000194 | 0.000084 |
| H32C | 0.000061 | 0.000182 | 0.000072 |

## Method

- **Calibration:** Shen 2018 force-0/force-1 protocol, P/N split-side
- **Targets:** 7 stages (H1, H2, H4, H8-R, H8-A, H16, H32)
- **Base ruler:** complete low segment plus terminal (131 Q0 total)
- **Calibration order:** H1->H2->H4->H8-R->H8-A->H16->H32
- **Decoder:** 15-stage P/N weights, direct Q2 weighted reconstruction
- **Static test:** exact deterministic decision-tree partition for every seed
- **FFT:** 4096-point, rectangular window (coherent sampling), bin k=127

## Known Limitations

- **Dynamic output:** Acceptance uses Q2 reconstruction. Integer 12-bit output
  is retained as a diagnostic because it adds a second quantization.
- **Static scope:** The exact reachable decision tree is an offline audit.
  It does not sort outputs, alter codes, or add a table to the decoder.
- **Reference scope:** Chen 2024 informs the local backend-range criterion;
  its auxiliary comparator and three-bridge circuit are not copied.
