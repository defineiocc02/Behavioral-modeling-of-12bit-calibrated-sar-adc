"""Independent full-transition static check for the active SRM-off path.

This is intentionally separate from the fast sampled static check in the
100-seed pipeline.  It measures every transition for a small number of seeds,
so the result is a real static sign-off sample rather than an interpolated
estimate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from python_cal import config as cfg
from python_cal.calibration.calibration_fsm import ADCOperatingMode
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.run_srm_off_isolation import _high_only_caps, _run_calibration
from python_cal.topology.cdac_topology import VCM, N_BITS


MAX_CODE = (1 << N_BITS) - 1


def make_adc(cdac: DifferentialCDAC, wp, wn) -> AsyncBehavioralSARADC:
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc._decoder = SARDecoder(weights_p=list(wp), weights_n=list(wn))
    adc._nominal_decode_enabled = True
    object.__setattr__(adc, "mode", ADCOperatingMode.READY)
    return adc


def find_transition(adc, decoder, target_code, v_lo, v_hi, iterations=30):
    for _ in range(iterations):
        mid = (v_lo + v_hi) / 2.0
        result = adc.convert(VCM + mid / 2.0, VCM - mid / 2.0)
        code = decoder.decode(list(result.decisions))
        if code <= target_code:
            v_lo = mid
        else:
            v_hi = mid
        if v_hi - v_lo < 1e-8:
            break
    return (v_lo + v_hi) / 2.0


def full_static(adc, decoder):
    v_neg = find_transition(adc, decoder, 0, -2.0, 0.0)
    v_pos = find_transition(adc, decoder, MAX_CODE - 1, 0.0, 2.0)
    transitions = {0: v_neg, MAX_CODE: v_pos}
    non_monotonic = []
    previous = v_neg
    for code in range(1, MAX_CODE):
        threshold = find_transition(adc, decoder, code, v_neg, v_pos)
        transitions[code] = threshold
        if threshold <= previous:
            non_monotonic.append(code)
        previous = threshold

    widths = np.array([
        transitions[c + 1] - transitions[c] for c in range(MAX_CODE)
    ])
    lsb = (v_pos - v_neg) / MAX_CODE
    dnl = widths / lsb - 1.0
    codes = np.arange(MAX_CODE + 1)
    inl = np.array([
        (transitions[c] - transitions[0] - c * lsb) / lsb
        for c in codes
    ])
    missing = np.flatnonzero(widths <= 0).tolist()
    interior = dnl[1:-1]
    peak_local = int(np.argmax(np.abs(interior))) + 1
    return {
        "sampled": False,
        "n_transitions": MAX_CODE - 1,
        "n_missing": len(missing),
        "missing_codes": missing[:20],
        "n_non_monotonic": len(non_monotonic),
        "non_monotonic": non_monotonic[:20],
        "dnl_peak_lsb": float(np.max(np.abs(dnl[1:-1]))),
        "dnl_peak_code": peak_local,
        "dnl_at_peak_lsb": float(dnl[peak_local]),
        "dnl_min_lsb": float(np.min(interior)),
        "dnl_max_lsb": float(np.max(interior)),
        "dnl_rms_lsb": float(np.sqrt(np.mean(dnl[1:-1] ** 2))),
        "inl_peak_lsb": float(np.max(np.abs(inl))),
        "inl_rms_lsb": float(np.sqrt(np.mean(inl ** 2))),
        "v_neg": float(v_neg),
        "v_pos": float(v_pos),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=70000)
    parser.add_argument("--avg-pairs", type=int, default=256)
    parser.add_argument("--cal-noise-sigma-v", type=float, default=0.0002)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent /
                                                "validation_results" /
                                                "static_signoff"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for offset in range(args.seeds):
        seed = args.seed_start + offset
        p_caps, n_caps = _high_only_caps(seed)
        cdac = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)

        nominal_adc = make_adc(cdac, cfg.NOMINAL_WEIGHTS_Q0, cfg.NOMINAL_WEIGHTS_Q0)
        nominal_static = full_static(
            nominal_adc,
            SARDecoder(weights_p=list(cfg.NOMINAL_WEIGHTS_Q0),
                       weights_n=list(cfg.NOMINAL_WEIGHTS_Q0)),
        )

        _, targets, wp, wn = _run_calibration(
            cdac, args.avg_pairs, args.cal_noise_sigma_v, seed + 50000, False
        )
        calibrated_static = full_static(
            make_adc(cdac, wp, wn),
            SARDecoder(weights_p=list(wp), weights_n=list(wn)),
        )
        rows.append({
            "seed": seed,
            "calibration_valid": bool(all(t["valid"] for t in targets)),
            "nominal": nominal_static,
            "calibrated": calibrated_static,
        })
        print(json.dumps(rows[-1], indent=2))

    result = {
        "scenario": "high-only mismatch; low segment and bridge exact nominal",
        "production_path": "Shen force-0/force-1, SRM-off",
        "seeds": args.seeds,
        "seed_start": args.seed_start,
        "avg_pairs": args.avg_pairs,
        "cal_noise_sigma_v": args.cal_noise_sigma_v,
        "rows": rows,
    }
    path = out / "full_static_signoff.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
