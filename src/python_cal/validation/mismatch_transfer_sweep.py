"""Mismatch-first transfer-integrity sweep for the active split CDAC.

This screen intentionally uses the *exact physical per-side weights* as the
decoder coefficients.  It therefore removes calibration estimator error and
comparator noise.  Any remaining backstep is caused by the physical redundant
decision tree plus the ordinary weighted-sum output mapping, not by an
insufficient number of calibration averages.

The closed-form two-node coefficients come directly from charge conservation:

    D = (Ch + Cb)(Cl + Cb) - Cb**2
    alpha_high_i = Ch_i (Cl + Cb) / D
    alpha_low_i  = Cl_i Cb / D

P and N arrays are drawn independently by summing mismatched unit capacitors.
Every reachable prefix interval is then partitioned analytically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from python_cal.validation.cdac_candidate_audit import _audit_seed


ACTIVE_CANDIDATE = {
    "high": [32, 16, 8, 8, 4, 2, 1],
    "bridge": 2,
    "low": [32, 16, 8, 4, 2, 2, 1],
    "terminal": 1.0,
}
SIGMA_POINTS = (0.0, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.02)


def _percentiles(rows: list[dict], key: str) -> dict[str, float]:
    values = np.asarray([row[key] for row in rows], dtype=float)
    return {
        "min": float(np.min(values)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
    }


def run_sweep(*, seed_start: int, seed_count: int) -> dict:
    if seed_count <= 0:
        raise ValueError("seed_count must be positive")
    points = []
    metric_keys = (
        "missing_codes",
        "integer_backsteps",
        "float_backsteps",
        "minimum_float_step_lsb",
        "worst_float_step_lsb",
        "worst_float_backstep_magnitude_lsb",
        "max_float_rollback_lsb",
        "max_integer_rollback_lsb",
        "float_nonmonotonic_input_fraction",
        "integer_nonmonotonic_input_fraction",
        "max_integer_jump",
        "dnl_peak_lsb",
        "inl_peak_lsb",
    )
    for sigma in SIGMA_POINTS:
        rows = [
            _audit_seed(
                **ACTIVE_CANDIDATE,
                seed=seed_start + offset,
                sigma=sigma,
            )
            for offset in range(seed_count)
        ]
        points.append({
            "unit_cap_sigma": sigma,
            "unit_cap_sigma_pct": sigma * 100.0,
            "strict_integer_monotonic_yield": int(sum(
                row["integer_backsteps"] == 0 for row in rows
            )),
            "zero_missing_code_yield": int(sum(
                row["missing_codes"] == 0 for row in rows
            )),
            "code_density_static_yield": int(sum(
                row["missing_codes"] == 0
                and row["max_integer_jump"] <= 1
                and row["dnl_peak_lsb"] <= 1.0
                and row["inl_peak_lsb"] <= 1.0
                for row in rows
            )),
            "metrics": {
                key: _percentiles(rows, key) for key in metric_keys
            },
        })
    return {
        "method": (
            "closed-form two-node charge-conservation coefficients plus "
            "exact reachable-prefix interval partition"
        ),
        "isolation": (
            "physical-oracle per-side weights; zero comparator/calibration "
            "noise; no calibration estimator"
        ),
        "interpretation": (
            "remaining violations isolate array mismatch, redundant decision "
            "ordering, and ordinary weighted-sum decode"
        ),
        "seed_start": seed_start,
        "seed_count": seed_count,
        "candidate": {
            **ACTIVE_CANDIDATE,
            "total_cu_per_side": (
                sum(ACTIVE_CANDIDATE["high"])
                + ACTIVE_CANDIDATE["bridge"]
                + sum(ACTIVE_CANDIDATE["low"])
            ),
        },
        "points": points,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=70000)
    parser.add_argument("--seed-count", type=int, default=1000)
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "validation_results"
            / "mismatch_transfer_sweep.json"
        ),
    )
    args = parser.parse_args()
    result = run_sweep(
        seed_start=args.seed_start,
        seed_count=args.seed_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(args.output)
    for point in result["points"]:
        metrics = point["metrics"]
        print(
            f"sigma={point['unit_cap_sigma_pct']:.3f}% "
            f"strict={point['strict_integer_monotonic_yield']}/"
            f"{result['seed_count']} "
            f"missing0={point['zero_missing_code_yield']}/"
            f"{result['seed_count']} "
            f"backsteps_p50={metrics['integer_backsteps']['p50']:.1f} "
            f"backstep_magnitude_p95="
            f"{metrics['worst_float_backstep_magnitude_lsb']['p95']:.4f} "
            f"LSB"
        )


if __name__ == "__main__":
    main()
