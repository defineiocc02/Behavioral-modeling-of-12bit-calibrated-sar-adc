"""SRM-off high-segment mismatch isolation experiment.

This is deliberately separate from the production pipeline.  It answers one
diagnostic question: with low segment and bridge ideal, how much of the high
segment mismatch can the observable Shen force-0/force-1 path recover?

The ``physical_low_oracle`` column is an offline upper-bound experiment.  It
is not a production calibration mode and must never be used to claim hardware
feasibility.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SRC_DIR)

from python_cal import config as cfg
from python_cal.async_control.timing import TimingParams
from python_cal.calibration.shen_calibrator import ShenCalibrationController
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.fft_metrics import compute_fft_coherent
from python_cal.validation.fft_protocol import (
    FFTProtocol,
    build_coherent_differential_sine,
    measure_positive_vfs,
)
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import CU, N_BITS, VCM, VREF


LOW_STAGES = tuple(cfg.BASE_RULER_STAGES)
HIGH_CAPS = tuple(
    name for name in cfg.ALL_CAP_NAMES if name.startswith("high_")
)


def _nominal_caps() -> dict[str, float]:
    return {name: CU * cfg.CAP_NOMINAL_CU[name] for name in cfg.ALL_CAP_NAMES}


def _high_only_caps(seed: int) -> tuple[dict[str, float], dict[str, float]]:
    """Low/bridge exact nominal; high caps have independent unit mismatch."""
    base = _nominal_caps()
    sides = []
    for side in (0, 1):
        rng = np.random.default_rng(seed * 2 + side)
        caps = dict(base)
        for name in HIGH_CAPS:
            count = cfg.CAP_NOMINAL_CU[name]
            caps[name] = sum(
                CU * float(rng.normal(1.0, cfg.MC_SIGMA))
                for _ in range(int(count))
            )
        sides.append(caps)
    return sides[0], sides[1]


def _run_calibration(cdac, avg_pairs: int, noise_sigma_v: float,
                     rng_seed: int, low_ruler_oracle: bool = False):
    physical = cdac.get_physical_weights_q0()
    base_wp = base_wn = None
    if low_ruler_oracle:
        base_wp = list(cfg.NOMINAL_WEIGHTS_Q0)
        base_wn = list(cfg.NOMINAL_WEIGHTS_Q0)
        for stage in LOW_STAGES:
            base_wp[stage] = physical[stage]
            base_wn[stage] = physical[stage]

    ctrl = ShenCalibrationController(
        cdac=cdac,
        comparator=DynamicComparator(),
        timing=TimingParams(),
        avg_pairs=avg_pairs,
        cal_noise_sigma=noise_sigma_v,
    )
    targets, wp, wn = ctrl.run(
        rng=np.random.default_rng(rng_seed),
        base_ruler_wp=base_wp,
        base_ruler_wn=base_wn,
    )
    return physical, targets, wp, wn


def _measure_vfs(cdac) -> float:
    from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
    from python_cal.calibration.calibration_fsm import ADCOperatingMode

    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc._decoder = SARDecoder(
        weights_p=list(cfg.NOMINAL_WEIGHTS_Q0),
        weights_n=list(cfg.NOMINAL_WEIGHTS_Q0),
    )
    adc._nominal_decode_enabled = True
    adc.mode = ADCOperatingMode.READY
    return measure_positive_vfs(
        lambda vd: adc.decode(
            adc.convert(VCM + vd / 2, VCM - vd / 2).decisions
        ),
        (1 << N_BITS) - 1,
        guard_codes=1,
    )


def _dynamic_metrics(cdac, wp, wn, vfs: float) -> dict[str, float]:
    protocol = FFTProtocol(
        n_fft=cfg.FFT_N,
        signal_bin=cfg.FFT_K,
        amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS,
        phase_rad=cfg.FFT_PHASE,
    )
    vin, metadata = build_coherent_differential_sine(vfs, protocol)
    from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
    from python_cal.calibration.calibration_fsm import ADCOperatingMode
    cdac_adc = AsyncBehavioralSARADC(cdac=cdac)
    cdac_adc._decoder = SARDecoder(
        weights_p=list(cfg.NOMINAL_WEIGHTS_Q0),
        weights_n=list(cfg.NOMINAL_WEIGHTS_Q0),
    )
    cdac_adc._nominal_decode_enabled = True
    cdac_adc.mode = ADCOperatingMode.READY
    decisions = []
    for vd in vin:
        result = cdac_adc.convert(VCM + vd / 2, VCM - vd / 2)
        decisions.append(list(result.decisions))
    decoded = [SARDecoder(weights_p=list(wp), weights_n=list(wn)).decode(d)
               for d in decisions]
    metrics = compute_fft_coherent(
        decoded,
        n_bits=N_BITS,
        n_fft=protocol.n_fft,
        signal_bin=protocol.signal_bin,
    )
    metrics.update({
        "vfs_v": float(vfs),
        "fft_amplitude_v": float(metadata["amplitude_v"]),
        "fft_peak_ratio_to_vfs": float(metadata["peak_ratio_to_vfs"]),
        "fft_clipping": bool(metadata["clipping"]),
    })
    return metrics


def run(args) -> dict:
    rows = []
    for index in range(args.seeds):
        seed = args.seed_start + index
        p_caps, n_caps = _high_only_caps(seed)
        cdac = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)
        physical, targets, wp, wn = _run_calibration(
            cdac, args.avg_pairs, args.cal_noise_sigma_v, seed + 50000, False
        )
        _, oracle_targets, oracle_wp, oracle_wn = _run_calibration(
            cdac, args.avg_pairs, args.cal_noise_sigma_v, seed + 50000, True
        )
        vfs = _measure_vfs(cdac)
        cal_metric = _dynamic_metrics(cdac, wp, wn, vfs)
        oracle_metric = _dynamic_metrics(cdac, oracle_wp, oracle_wn, vfs)
        nominal_metric = _dynamic_metrics(
            cdac, cfg.NOMINAL_WEIGHTS_Q0, cfg.NOMINAL_WEIGHTS_Q0, vfs
        )
        rows.append({
            "seed": seed,
            "valid": bool(all(t["valid"] for t in targets)),
            "oracle_valid": bool(all(t["valid"] for t in oracle_targets)),
            "nominal_enob": nominal_metric["enob"],
            "calibrated_enob": cal_metric["enob"],
            "physical_low_oracle_enob": oracle_metric["enob"],
            "calibrated_sndr_db": cal_metric["sndr_db"],
            "physical_low_oracle_sndr_db": oracle_metric["sndr_db"],
            "nominal_sndr_db": nominal_metric["sndr_db"],
            "fft_vfs_v": cal_metric["vfs_v"],
            "fft_amplitude_v": cal_metric["fft_amplitude_v"],
            "fft_peak_ratio_to_vfs": cal_metric["fft_peak_ratio_to_vfs"],
            "fft_clipping": cal_metric["fft_clipping"],
            "mean_high_weight_error_q0": float(np.mean([
                abs(wp[s] - physical[s]) for s in cfg.SHEN_CAL_TARGET_STAGES
            ])),
            "max_high_weight_error_q0": float(max(
                abs(wp[s] - physical[s]) for s in cfg.SHEN_CAL_TARGET_STAGES
            )),
            "oracle_mean_high_weight_error_q0": float(np.mean([
                abs(oracle_wp[s] - physical[s]) for s in cfg.SHEN_CAL_TARGET_STAGES
            ])),
        })

    def pct(key, q):
        return float(np.percentile([row[key] for row in rows], q))

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeds": args.seeds,
        "seed_start": args.seed_start,
        "mc_sigma": cfg.MC_SIGMA,
        "avg_pairs": args.avg_pairs,
        "cal_noise_sigma_v": args.cal_noise_sigma_v,
        "scenario": "high-only mismatch; low segment and bridge exact nominal",
        "production_path": "Shen force-0/force-1, SRM-off",
        "physical_low_oracle_is_diagnostic_only": True,
        "calibrated_enob_p50": pct("calibrated_enob", 50),
        "calibrated_enob_p95": pct("calibrated_enob", 95),
        "oracle_enob_p50": pct("physical_low_oracle_enob", 50),
        "nominal_enob_p50": pct("nominal_enob", 50),
        "calibrated_enob_gt_11_5_count": sum(
            row["calibrated_enob"] > 11.5 for row in rows
        ),
        "oracle_enob_gt_11_5_count": sum(
            row["physical_low_oracle_enob"] > 11.5 for row in rows
        ),
        "high_weight_mae_p50_q0": pct("mean_high_weight_error_q0", 50),
        "oracle_high_weight_mae_p50_q0": pct("oracle_mean_high_weight_error_q0", 50),
        "rows": rows,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--seed-start", type=int, default=70000)
    parser.add_argument("--avg-pairs", type=int, default=256)
    parser.add_argument("--cal-noise-sigma-v", type=float, default=0.0002)
    parser.add_argument("--out", default=os.path.join(
        SCRIPT_DIR, "validation_results", "srm_off_isolation"
    ))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    summary = run(args)
    path = os.path.join(args.out, "high_only_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    csv_path = os.path.join(args.out, "high_only_rows.csv")
    fields = [k for k in summary["rows"][0] if k != "seed"]
    fields = ["seed"] + fields
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary["rows"])
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"saved: {path}")
    print(f"saved: {csv_path}")


if __name__ == "__main__":
    main()
