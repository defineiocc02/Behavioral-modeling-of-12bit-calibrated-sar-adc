"""Fast reproducible comparison of retired and current CDAC candidates.

This verifier uses the closed-form two-node split-CDAC coefficients and an
exact vectorized prefix-interval partition.  It is independent of the slower
production charge-solver audit and is intended for architecture screening.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SIGMA = 0.005
VREF_HALF = 0.9
N_CODES = 4096


def _side_coefficients(rng, high, low, bridge, sigma=None):
    sigma = SIGMA if sigma is None else float(sigma)

    def group(count):
        return float(rng.normal(1.0, sigma, count).sum())

    high_c = np.asarray([group(value) for value in high])
    low_c = np.asarray([group(value) for value in low])
    bridge_c = group(bridge)
    determinant = (
        (high_c.sum() + bridge_c) * (low_c.sum() + bridge_c)
        - bridge_c**2
    )
    return np.r_[
        (low_c.sum() + bridge_c) / determinant * high_c,
        bridge_c / determinant * low_c,
    ]


def _audit_seed(high, low, bridge, terminal, seed, sigma=None):
    rng = np.random.default_rng(seed)
    p = _side_coefficients(rng, high, low, bridge, sigma=sigma)
    n = _side_coefficients(rng, high, low, bridge, sigma=sigma)
    input_slope = (p.sum() + n.sum()) / 2.0
    nominal = np.asarray(
        [value * (sum(low) + bridge) for value in high]
        + [value * bridge for value in low],
        dtype=float,
    )
    scale = nominal.sum() / (VREF_HALF * input_slope)
    weights = VREF_HALF * (p + n) / 2.0 * scale

    lo = np.asarray([-2.0])
    hi = np.asarray([2.0])
    residue = np.asarray([0.0])
    decoded = np.asarray([0.0])
    tolerance = 1e-12

    for stage, weight in enumerate(weights):
        root = (
            residue + VREF_HALF * (p[stage] - n[stage])
        ) / input_slope
        split = (root > lo + tolerance) & (root < hi - tolerance)
        middle = (lo + hi) / 2.0
        decision_one = (
            -input_slope * middle
            + residue
            + VREF_HALF * (p[stage] - n[stage])
        ) > 0.0

        unsplit_lo = lo[~split]
        unsplit_hi = hi[~split]
        unsplit_residue = residue[~split] + np.where(
            decision_one[~split],
            -VREF_HALF * n[stage],
            VREF_HALF * p[stage],
        )
        unsplit_decoded = decoded[~split] + np.where(
            decision_one[~split], -weight, weight
        )

        split_root = root[split]
        split_lo = lo[split]
        split_hi = hi[split]
        split_residue = residue[split]
        split_decoded = decoded[split]
        lo = np.r_[unsplit_lo, split_lo, split_root]
        hi = np.r_[unsplit_hi, split_root, split_hi]
        residue = np.r_[
            unsplit_residue,
            split_residue - VREF_HALF * n[stage],
            split_residue + VREF_HALF * p[stage],
        ]
        decoded = np.r_[
            unsplit_decoded,
            split_decoded - weight,
            split_decoded + weight,
        ]

    # Comparator-only terminal decision.
    root = residue / input_slope
    split = (root > lo + tolerance) & (root < hi - tolerance)
    middle = (lo + hi) / 2.0
    decision_one = (-input_slope * middle + residue) > 0.0
    unsplit_lo = lo[~split]
    unsplit_hi = hi[~split]
    unsplit_decoded = decoded[~split] + np.where(
        decision_one[~split], -terminal, terminal
    )
    split_root = root[split]
    split_lo = lo[split]
    split_hi = hi[split]
    split_decoded = decoded[split]
    lo = np.r_[unsplit_lo, split_lo, split_root]
    hi = np.r_[unsplit_hi, split_root, split_hi]
    decoded = np.r_[
        unsplit_decoded,
        split_decoded - terminal,
        split_decoded + terminal,
    ]

    order = np.argsort(lo)
    lo = lo[order]
    hi = hi[order]
    code_float = np.clip(
        (decoded[order] + weights.sum())
        * (N_CODES - 1)
        / (2.0 * weights.sum()),
        0,
        N_CODES - 1,
    )
    codes = np.floor(code_float + 0.5).astype(int)
    float_steps = np.diff(code_float)
    steps = np.diff(codes)
    represented = np.zeros(N_CODES, dtype=bool)
    represented[codes] = True

    # A backstep count alone is dominated by how many exactly tied nominal
    # boundaries are split by an arbitrarily small mismatch.  Also report the
    # amplitude and the fraction of the input interval that is actually below
    # the previously reached code.  These quantify severity without hiding the
    # order violation.
    prior_float_max = np.maximum.accumulate(code_float)
    prior_integer_max = np.maximum.accumulate(codes)
    float_violation = code_float < prior_float_max - tolerance
    integer_violation = codes < prior_integer_max
    interval_width = hi - lo
    input_span = float(hi[-1] - lo[0])

    widths = np.bincount(codes, weights=hi - lo, minlength=N_CODES)
    internal = widths[1:-1]
    ideal = internal.mean()
    dnl = internal / ideal - 1.0
    inl = np.cumsum(dnl)
    inl -= np.linspace(inl[0], inl[-1], len(inl))
    return {
        "missing_codes": int(np.count_nonzero(~represented)),
        "integer_backsteps": int(np.count_nonzero(steps < 0)),
        "float_backsteps": int(np.count_nonzero(float_steps < -tolerance)),
        "minimum_float_step_lsb": float(np.min(float_steps)),
        "worst_float_step_lsb": float(min(0.0, np.min(float_steps))),
        "worst_float_backstep_magnitude_lsb": float(
            max(0.0, -np.min(float_steps))
        ),
        "max_float_rollback_lsb": float(
            np.max(prior_float_max - code_float)
        ),
        "max_integer_rollback_lsb": int(
            np.max(prior_integer_max - codes)
        ),
        "float_nonmonotonic_input_fraction": float(
            np.sum(interval_width[float_violation]) / input_span
        ),
        "integer_nonmonotonic_input_fraction": float(
            np.sum(interval_width[integer_violation]) / input_span
        ),
        "max_integer_jump": int(np.max(steps)),
        "dnl_peak_lsb": float(np.max(np.abs(dnl))),
        "inl_peak_lsb": float(np.max(np.abs(inl))),
    }


def _summarize(rows):
    result = {"seeds": len(rows)}
    for key in rows[0]:
        values = np.asarray([row[key] for row in rows], dtype=float)
        result[key] = {
            "min": float(np.min(values)),
            "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)),
            "max": float(np.max(values)),
        }
    result["zero_missing_yield"] = int(
        sum(row["missing_codes"] == 0 for row in rows)
    )
    result["paper_static_yield"] = int(sum(
        row["missing_codes"] == 0
        and row["max_integer_jump"] <= 1
        and row["dnl_peak_lsb"] <= 1.0
        and row["inl_peak_lsb"] <= 1.0
        for row in rows
    ))
    return result


def main():
    candidates = {
        "retired_95cu": {
            "high": [16, 8, 4, 2, 1],
            "bridge": 1,
            "low": [24, 16, 10, 6, 4, 2, 1],
            "terminal": 0.5,
        },
        "v3_138cu": {
            "high": [32, 16, 8, 8, 4, 2, 1],
            "bridge": 2,
            "low": [32, 16, 8, 4, 2, 2, 1],
            "terminal": 1.0,
        },
    }
    output = {
        "method": "closed-form split-CDAC exact reachable interval audit",
        "unit_cap_sigma": SIGMA,
        "seed_start": 50000,
        "seed_count": 1000,
        "candidates": {},
    }
    for name, candidate in candidates.items():
        rows = [
            _audit_seed(
                candidate["high"],
                candidate["low"],
                candidate["bridge"],
                candidate["terminal"],
                50000 + offset,
            )
            for offset in range(1000)
        ]
        output["candidates"][name] = {
            **candidate,
            "total_cu": (
                sum(candidate["high"])
                + candidate["bridge"]
                + sum(candidate["low"])
            ),
            "summary": _summarize(rows),
        }

    destination = (
        Path(__file__).resolve().parents[1]
        / "validation_results"
        / "cdac_design_audit.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(destination)
    print(json.dumps(output["candidates"], indent=2))


if __name__ == "__main__":
    main()
