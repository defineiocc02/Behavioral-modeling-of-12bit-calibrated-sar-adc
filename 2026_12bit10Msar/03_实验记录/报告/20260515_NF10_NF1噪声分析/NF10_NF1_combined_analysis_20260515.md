# NF=10 / NF=1 Noise Simulation Combined Report

Generated: 2026-05-15 HKT  
Circuit: new structure, comparator critical devices verified as NF=10 equivalent `m=10` in the netlist.  
Data scope: current Maestro `ExplorerRun.0` only. Older Interactive runs are excluded.

## Executive Summary

Both raw result sets have been captured on the host machine:

- NF=10 / `noisescale=10`: user-defined sample-noise-only stress mode, 20 points, all Spectre runs completed with 0 errors.
- NF=1 / `noisescale=1`: user-defined full-noise mode, 20 points, all Spectre runs completed with 0 errors.
- The report analyzes each process corner separately: Nominal, C0, C1, fs, and sf. Averages are not used as the main conclusion.

Important interpretation: NF=10 and NF=1 are not equal-scale noise runs. NF=10 intentionally stresses the selected sampling-noise contribution, so it has lower SNR than NF=1. The useful comparison is the corner-by-corner td trend and the relative stress gap, not a simple statement that one physical noise source is larger.

## Fixed Data Files

- `reports/NF10_raw_measurements_20260515.csv`: raw ADE measurements for NF=10, 20 rows.
- `reports/NF1_raw_measurements_20260515.csv`: raw ADE measurements for NF=1, 20 rows.
- `reports/NF10_NF1_raw_measurements_20260515.csv`: combined raw table, 40 rows.
- `reports/NF10_NF1_noise_calculated_20260515.csv`: combined table with derived noise powers and RMS values.

## Noise Calculation

Main assumption: `VFS = Vref = 1 Vpp`, 12-bit ADC.

`LSB = VFS / 2^12 = 244.141 uV`  
`Vq,rms = LSB / sqrt(12) = 70.477 uV`  
`Pq = Vq,rms^2 = 4.967054e-9 V^2`  
`Psig = (VFS / (2 sqrt(2)))^2 = 0.125000 V^2`

For each raw SNR result:

`Ptotal = Psig / 10^(SNR/10)`  
`Pexcess = max(Ptotal - Pq, 0)`  
`Vexcess,rms = sqrt(Pexcess)`

If the final project convention is differential full-scale `VFS = 2 * Vref`, RMS values scale by 2 and power values scale by 4. The td optimum and corner trends are unchanged.

## Best td By Corner

| corner | NF=10 best td | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=1 best td | NF=1 SNR | NF=1 ENOB | NF=1 SFDR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Nominal | 27n | 64.244 | 10.333 | 75.278 | 25n | 68.437 | 11.103 | 76.687 |
| C0 | 26n | 64.404 | 10.420 | 75.229 | 25n | 69.545 | 11.204 | 78.695 |
| C1 | 27n | 61.544 | 9.948 | 72.968 | 25n | 67.799 | 10.921 | 79.667 |
| fs | 26n | 64.855 | 10.462 | 77.562 | 25n | 69.121 | 11.162 | 81.083 |
| sf | 27n | 61.830 | 9.916 | 73.576 | 27n | 67.934 | 11.026 | 78.176 |


## Figures

![SNR by corner](snr_by_corner.svg)

![ENOB by corner](enob_by_corner.svg)

![SFDR by corner](sfdr_by_corner.svg)

![Excess noise power by corner](excess_noise_power_by_corner.svg)

![SNR delta](snr_delta_nf1_minus_nf10.svg)

![NF10 heatmap](nf10_excess_noise_heatmap.svg)

![NF1 heatmap](nf1_excess_noise_heatmap.svg)

## Corner-by-Corner Analysis

### Nominal

| td | Delta td ns | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=10 Pexcess V^2 | NF=1 SNR | NF=1 ENOB | NF=1 SFDR | NF=1 Pexcess V^2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24.05n | 0.05 | 54.898 | 8.760 | 66.318 | 3.997e-7 | 67.952 | 11.013 | 81.432 | 1.506e-8 |
| 25n | 1.00 | 59.542 | 9.531 | 69.765 | 1.339e-7 | 68.437 | 11.103 | 76.687 | 1.295e-8 |
| 26n | 2.00 | 61.787 | 9.948 | 74.033 | 7.787e-8 | 67.390 | 10.963 | 77.140 | 1.783e-8 |
| 27n | 3.00 | 64.244 | 10.333 | 75.278 | 4.207e-8 | 67.346 | 10.943 | 78.346 | 1.806e-8 |

NF=10 best SNR occurs at 27n: 64.244 dB, ENOB 10.333, SFDR 75.278, Pexcess 4.207e-8 V^2. NF=1 best SNR occurs at 25n: 68.437 dB, ENOB 11.103, SFDR 76.687, Pexcess 1.295e-8 V^2. Nominal improves through 27 ns in the NF=10 stress run, while NF=1 peaks earlier at 25 ns.

### C0

| td | Delta td ns | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=10 Pexcess V^2 | NF=1 SNR | NF=1 ENOB | NF=1 SFDR | NF=1 Pexcess V^2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24.05n | 0.05 | 56.977 | 9.109 | 67.896 | 2.458e-7 | 68.508 | 11.089 | 79.105 | 1.266e-8 |
| 25n | 1.00 | 62.915 | 10.141 | 73.921 | 5.892e-8 | 69.545 | 11.204 | 78.695 | 8.913e-9 |
| 26n | 2.00 | 64.404 | 10.420 | 75.229 | 4.038e-8 | 68.385 | 11.080 | 79.438 | 1.316e-8 |
| 27n | 3.00 | 63.801 | 10.332 | 74.814 | 4.713e-8 | 64.938 | 10.484 | 76.730 | 3.513e-8 |

NF=10 best SNR occurs at 26n: 64.404 dB, ENOB 10.420, SFDR 75.229, Pexcess 4.038e-8 V^2. NF=1 best SNR occurs at 25n: 69.545 dB, ENOB 11.204, SFDR 78.695, Pexcess 8.913e-9 V^2. The stressed sampling-noise run peaks before 27 ns, so delaying td past the local optimum can start to lose margin in this corner.

### C1

| td | Delta td ns | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=10 Pexcess V^2 | NF=1 SNR | NF=1 ENOB | NF=1 SFDR | NF=1 Pexcess V^2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24.05n | 0.05 | 53.004 | 8.543 | 65.535 | 6.209e-7 | 67.518 | 10.964 | 78.431 | 1.717e-8 |
| 25n | 1.00 | 57.216 | 9.234 | 67.936 | 2.323e-7 | 67.799 | 10.921 | 79.667 | 1.578e-8 |
| 26n | 2.00 | 60.480 | 9.799 | 71.930 | 1.070e-7 | 67.439 | 10.928 | 78.799 | 1.758e-8 |
| 27n | 3.00 | 61.544 | 9.948 | 72.968 | 8.264e-8 | 67.637 | 10.890 | 79.841 | 1.657e-8 |

NF=10 best SNR occurs at 27n: 61.544 dB, ENOB 9.948, SFDR 72.968, Pexcess 8.264e-8 V^2. NF=1 best SNR occurs at 25n: 67.799 dB, ENOB 10.921, SFDR 79.667, Pexcess 1.578e-8 V^2. The stressed sampling-noise run continues improving through 27 ns in this corner, although the NF=1 run has its own optimum.

### fs

| td | Delta td ns | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=10 Pexcess V^2 | NF=1 SNR | NF=1 ENOB | NF=1 SFDR | NF=1 Pexcess V^2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24.05n | 0.05 | 56.247 | 8.991 | 67.776 | 2.917e-7 | 68.188 | 11.059 | 79.445 | 1.401e-8 |
| 25n | 1.00 | 61.772 | 9.890 | 72.561 | 7.815e-8 | 69.121 | 11.162 | 81.083 | 1.034e-8 |
| 26n | 2.00 | 64.855 | 10.462 | 77.562 | 3.590e-8 | 68.461 | 11.098 | 79.421 | 1.285e-8 |
| 27n | 3.00 | 63.720 | 10.270 | 74.767 | 4.811e-8 | 64.437 | 10.401 | 75.686 | 4.003e-8 |

NF=10 best SNR occurs at 26n: 64.855 dB, ENOB 10.462, SFDR 77.562, Pexcess 3.590e-8 V^2. NF=1 best SNR occurs at 25n: 69.121 dB, ENOB 11.162, SFDR 81.083, Pexcess 1.034e-8 V^2. The stressed sampling-noise run peaks before 27 ns, so delaying td past the local optimum can start to lose margin in this corner.

### sf

| td | Delta td ns | NF=10 SNR | NF=10 ENOB | NF=10 SFDR | NF=10 Pexcess V^2 | NF=1 SNR | NF=1 ENOB | NF=1 SFDR | NF=1 Pexcess V^2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24.05n | 0.05 | 53.727 | 8.561 | 64.167 | 5.250e-7 | 67.931 | 10.898 | 79.007 | 1.516e-8 |
| 25n | 1.00 | 58.080 | 9.311 | 69.511 | 1.895e-7 | 67.246 | 10.871 | 77.103 | 1.860e-8 |
| 26n | 2.00 | 60.378 | 9.677 | 70.525 | 1.096e-7 | 67.084 | 10.878 | 78.409 | 1.950e-8 |
| 27n | 3.00 | 61.830 | 9.916 | 73.576 | 7.706e-8 | 67.934 | 11.026 | 78.176 | 1.515e-8 |

NF=10 best SNR occurs at 27n: 61.830 dB, ENOB 9.916, SFDR 73.576, Pexcess 7.706e-8 V^2. NF=1 best SNR occurs at 27n: 67.934 dB, ENOB 11.026, SFDR 78.176, Pexcess 1.515e-8 V^2. The stressed sampling-noise run continues improving through 27 ns in this corner, although the NF=1 run has its own optimum.

## Engineering Readout

- NF=10 sample-noise stress mode shows that td movement is a real control knob for sampling-noise cancellation. The optimum is corner-dependent: Nominal/C1/sf prefer 27 ns by SNR, while C0/fs prefer 26 ns.
- NF=1 full-noise mode is cleaner in absolute SNR because the run uses `noisescale=1`, while the NF=10 run deliberately stresses sampling noise with `noisescale=10`.
- For robust design choice, do not choose td from a global average. Choose based on the corner that sets the acceptance risk. If C0/fs high-speed behavior is limiting, 26 ns deserves attention; if Nominal/C1/sf sampling cancellation dominates, 27 ns looks favorable.
- The final report should keep raw ADE measurements and derived noise estimates in separate tables. The derived Pexcess values depend on the VFS convention, but SNR/ENOB/SFDR do not.
