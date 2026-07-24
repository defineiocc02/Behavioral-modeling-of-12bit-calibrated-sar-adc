"""Independent baseline diagnosis for the split-CDAC SNDR gap.

This script deliberately does not run calibration and does not use SRM.  It
compares the same coherent stimulus through:

1. an ideal mathematical quantizer,
2. the nominal decoder after the ideal physical split-CDAC makes decisions,
3. the physical-weight decoder after the same decisions.

The second and third cases retain the analog charge/decision path, so they are
not an oracle for the analog model.  The output is intended to separate a
test-bench/reference problem from a deterministic topology/model baseline.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from python_cal import config as cfg
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.fft_metrics import compute_fft_coherent
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import VCM, VREF, N_BITS
from python_cal.calibration.calibration_fsm import ADCOperatingMode


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "validation_results" / "baseline_diagnosis"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_adc(cdac: DifferentialCDAC, decoder: SARDecoder) -> AsyncBehavioralSARADC:
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc._decoder = decoder
    adc._nominal_decode_enabled = True
    object.__setattr__(adc, "mode", ADCOperatingMode.READY)
    return adc


def convert_code(adc: AsyncBehavioralSARADC, vd: float, decoder: SARDecoder) -> int:
    result = adc.convert(VCM + vd / 2.0, VCM - vd / 2.0)
    return decoder.decode(list(result.decisions))


def measure_vfs(adc: AsyncBehavioralSARADC, decoder: SARDecoder) -> float:
    max_code = (1 << N_BITS) - 1
    lo, hi = 0.0, 2.0
    for _ in range(10):
        if convert_code(adc, hi, decoder) >= max_code - 1:
            break
        hi *= 1.5
    for _ in range(24):
        mid = (lo + hi) / 2.0
        if convert_code(adc, mid, decoder) >= max_code - 1:
            hi = mid
        else:
            lo = mid
    return float(hi)


def measure_path(adc: AsyncBehavioralSARADC, vin: np.ndarray,
                 vfs: float, physical_weights: list[float]) -> dict:
    """Measure all three decoder/reference paths for one stimulus."""
    max_code = (1 << N_BITS) - 1
    nominal_decoder = SARDecoder(weights_p=list(cfg.NOMINAL_WEIGHTS_Q0),
                                 weights_n=list(cfg.NOMINAL_WEIGHTS_Q0))
    physical_decoder = SARDecoder(weights_p=physical_weights,
                                  weights_n=physical_weights)
    decisions = []
    nominal_codes = []
    for vd in vin:
        result = adc.convert(VCM + vd / 2.0, VCM - vd / 2.0)
        decisions.append(list(result.decisions))
        nominal_codes.append(nominal_decoder.decode(list(result.decisions)))
    physical_codes = [physical_decoder.decode(d) for d in decisions]
    ideal_codes = np.rint((vin / vfs + 1.0) * max_code / 2.0)
    ideal_codes = np.clip(ideal_codes, 0, max_code).astype(int).tolist()
    return {
        "mathematical_ideal": compute_fft_coherent(
            ideal_codes, n_bits=N_BITS, n_fft=len(vin), signal_bin=int(cfg.FFT_K)
        ),
        "physical_ideal_nominal_decoder": compute_fft_coherent(
            nominal_codes, n_bits=N_BITS, n_fft=len(vin), signal_bin=int(cfg.FFT_K)
        ),
        "physical_ideal_physical_weight_decoder": compute_fft_coherent(
            physical_codes, n_bits=N_BITS, n_fft=len(vin), signal_bin=int(cfg.FFT_K)
        ),
    }


def main() -> None:
    n_fft = int(cfg.FFT_N)
    k = int(cfg.FFT_K)
    max_code = (1 << N_BITS) - 1
    nominal = list(cfg.NOMINAL_WEIGHTS_Q0)

    # No mismatch: this is the deterministic topology/model baseline.
    cdac = DifferentialCDAC.ideal()
    nominal_decoder = SARDecoder(weights_p=nominal, weights_n=nominal)
    adc = make_adc(cdac, nominal_decoder)
    vfs = measure_vfs(adc, nominal_decoder)
    amp = vfs * (10.0 ** (float(cfg.FFT_AMPLITUDE_DBFS) / 20.0))
    t = np.arange(n_fft)
    vin = amp * np.sin(2.0 * np.pi * k * t / n_fft + float(cfg.FFT_PHASE))

    physical_weights = cdac.get_physical_weights_q0()
    # Current reference: dynamically measured VFS.
    metrics = measure_path(adc, vin, vfs, physical_weights)

    # Legacy reference found in older runs: fixed 0.45*VREF amplitude. This
    # is kept only to explain why old artifacts reported approximately 72.2 dB.
    legacy_amp = VREF * 0.45 * (10.0 ** (float(cfg.FFT_AMPLITUDE_DBFS) / 20.0))
    legacy_vin = legacy_amp * np.sin(
        2.0 * np.pi * k * t / n_fft + float(cfg.FFT_PHASE)
    )
    legacy_metrics = measure_path(adc, legacy_vin, vfs, physical_weights)

    names = ["L32C", "L16C", "L8C", "L4C", "L2C", "L1C", "T1C"]
    low_nominal = [64.0, 32.0, 16.0, 8.0, 4.0, 2.0, 1.0]
    low_effective = [float(physical_weights[i]) for i in range(7, 14)]
    effective_ratio = [w / n for w, n in zip(low_effective, low_nominal)]

    result = {
        "model": "DifferentialCDAC.ideal()",
        "srm_used": False,
        "n_fft": n_fft,
        "fft_bin": k,
        "fft_amplitude_dbfs": float(cfg.FFT_AMPLITUDE_DBFS),
        "measured_vfs": vfs,
        "stimulus_peak_v": amp,
        "metrics": metrics,
        "legacy_fixed_0p45_vref": {
            "stimulus_peak_v": legacy_amp,
            "metrics": legacy_metrics,
            "note": "Diagnostic only; not the current dynamic-VFS pipeline reference.",
        },
        "physical_weights_q0": [float(x) for x in physical_weights],
        "low_segment": [
            {"stage": n, "nominal_q0": n0, "effective_q0": w, "ratio": r}
            for n, n0, w, r in zip(names, low_nominal, low_effective, effective_ratio)
        ],
        "sndr_gap_math_to_physical_db": (
            metrics["mathematical_ideal"]["sndr_db"]
            - metrics["physical_ideal_nominal_decoder"]["sndr_db"]
        ),
        "interpretation": (
            "The physical cases retain the analog charge/decision path; the gap "
            "is therefore a deterministic baseline diagnostic, not evidence of "
            "random mismatch or an SRM requirement."
        ),
    }

    out = OUT_DIR / "baseline_diagnosis.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
