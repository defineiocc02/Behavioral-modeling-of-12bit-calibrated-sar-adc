# FFT Validation Protocol Audit

Date: 2026-07-24

Scope: read-only review of `src/python_cal`, excluding `archive/`, `review/`,
and `validation_results/`.

## Executive conclusion

The current main calibration pipeline and `run_srm_off_isolation.py` use the
same coherent FFT stimulus definition:

- FFT length: 4096 samples
- coherent signal bin: 127
- phase: 0.123 rad
- nominal sample rate: 10 MHz
- input amplitude: -0.5 dBFS relative to a dynamically measured positive VFS

`gcd(4096, 127) = 1`; the record contains exactly 127 input cycles. With the
configured sample rate, the input frequency is 310058.59375 Hz.

The historical fixed-amplitude definition `0.45 * VREF` is no longer used by
the current `run_srm_off_isolation.py`. It remains only as an explicitly
labelled legacy comparison in `run_baseline_diagnosis.py`.

## Minimal experiment

The experiment used `DifferentialCDAC.ideal()`, the nominal decoder, and the
same 4096-point, bin-127, phase-0.123 stimulus for both amplitude definitions.
No project file was written.

| Measurement | Dynamic VFS protocol | Legacy 0.45*VREF protocol |
|---|---:|---:|
| Measured VFS | 0.859157213 V | 0.859157213 V |
| Input peak | 0.811096679 V | 0.764689279 V |
| Actual amplitude | -0.500000 dBFS | -1.011753 dBFS |
| Minimum / maximum code | 116 / 3979 | 227 / 3868 |
| Endpoint clipping samples | 0 | 0 |
| SNDR | 72.702 dB | 72.160 dB |
| ENOB | 11.784 bit | 11.694 bit |

The legacy definition lowers measured SNDR by 0.542 dB and ENOB by 0.090 bit.
Results produced under the two definitions must therefore not be pooled under
one absolute acceptance threshold.

## Active FFT paths

- `validation/fft_protocol.py`: authoritative coherent-stimulus builder and
  validation metadata.
- `run_final_calibration_pipeline.py`: dynamic VFS, shared stimulus, explicit
  stimulus clipping rejection.
- `run_srm_off_isolation.py`: dynamic VFS and the same shared stimulus.
- `run_isolation_experiment.py`: matching N/K/phase/amplitude, but retains a
  local implementation and a silent `0.4773 * VREF` fallback.
- `test_observable_alpha.py`: matching configuration, but also retains the
  local implementation and fallback.
- `run_baseline_diagnosis.py`: dynamic VFS for the current reference plus an
  explicitly labelled legacy `0.45 * VREF` diagnostic.
- `close_ideal_baseline.py`: diagnostic-only local FFT using `0.95 * VFS`
  (-0.4455 dBFS), so it is not protocol-equivalent to the acceptance path.

## Remaining limitations

1. VFS is measured only on the positive differential-input side; negative-side
   asymmetry is not independently bounded.
2. The main pipeline checks stimulus-domain clipping, but does not count raw
   decoder over-range events for every calibrated weight set.
3. `run_isolation_experiment.py` and `test_observable_alpha.py` have not yet
   migrated to the shared protocol module.
4. The current SFDR implementation excludes H2-H7 from the spur search.
   Reported SFDR is therefore not standard SFDR including harmonic spurs.
5. `FFT_FS` supplies physical-frequency metadata but is not coupled to an
   independently verified converter timing stream in the behavioral scripts.

## Acceptance statement

Coherent sampling and record length pass for the main and current SRM-off
paths. Their amplitude and VFS definitions are now consistent. Historical
fixed-`0.45*VREF` results require separate labelling or rerun before comparison
against the current absolute SNDR/ENOB gates.
