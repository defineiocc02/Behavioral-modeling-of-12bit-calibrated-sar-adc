"""Audit the deterministic H4 carry margin of the 14-decision codebook.

This is a read-only model audit except for its JSON result.  It uses the
independent P/N physical-weight oracle and does not run or assist calibration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from python_cal import config as cfg
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import CU


def generate_caps(seed: int) -> tuple[dict[str, float], dict[str, float]]:
    rng = np.random.default_rng(seed)
    sides = []
    for _ in range(2):
        caps = {}
        for name in cfg.ALL_CAP_NAMES:
            units = int(cfg.CAP_NOMINAL_CU[name])
            caps[name] = sum(
                CU * float(rng.normal(1.0, cfg.MC_SIGMA))
                for _ in range(units)
            )
        sides.append(caps)
    return sides[0], sides[1]


def h4_carry_margin(weights_p, weights_n) -> float:
    """Weighted-sum delta for the observed H4 carry transition, in Q0."""
    side_sum = [
        float(weights_p[i] + weights_n[i]) for i in range(cfg.N_STAGES)
    ]
    return (
        side_sum[3]
        - sum(side_sum[i] for i in (4, 5, 6, 7))
        + sum(side_sum[i] for i in range(8, 14))
    )


def run(seeds: int, seed_start: int) -> dict:
    rows = []
    for seed in range(seed_start, seed_start + seeds):
        p_caps, n_caps = generate_caps(seed)
        cdac = DifferentialCDAC.from_mismatch(
            p_caps=p_caps, n_caps=n_caps
        )
        weights_p, weights_n = cdac.get_physical_weights_per_side_q0()
        margin = h4_carry_margin(weights_p, weights_n)
        rows.append({
            "seed": seed,
            "h4_carry_margin_q0": margin,
            "required_symmetric_h1r_decrement_q0": max(0.0, -margin / 2.0),
        })

    margins = np.array([row["h4_carry_margin_q0"] for row in rows])
    guards = np.array([
        row["required_symmetric_h1r_decrement_q0"] for row in rows
    ])
    ideal = list(cfg.NOMINAL_WEIGHTS_Q0)
    return {
        "seeds": seeds,
        "seed_start": seed_start,
        "mc_sigma": cfg.MC_SIGMA,
        "ideal_h4_carry_margin_q0": h4_carry_margin(ideal, ideal),
        "negative_margin_count": int(np.sum(margins < 0.0)),
        "margin_q0": {
            "min": float(np.min(margins)),
            "p05": float(np.percentile(margins, 5)),
            "p50": float(np.percentile(margins, 50)),
            "p95": float(np.percentile(margins, 95)),
            "max": float(np.max(margins)),
        },
        "required_symmetric_h1r_decrement_q0": {
            "p50": float(np.percentile(guards, 50)),
            "p95": float(np.percentile(guards, 95)),
            "max": float(np.max(guards)),
        },
        "interpretation": (
            "A negative margin means the true weighted reconstruction steps "
            "backward at the observed H4 carry. A fixed H1R decrement is only "
            "a diagnostic: it can move missing codes to other boundaries and "
            "is not an accepted repair."
        ),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=10000)
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parent
            / "validation_results"
            / "codebook_margin"
            / "h4_carry_margin.json"
        ),
    )
    args = parser.parse_args()
    result = run(args.seeds, args.seed_start)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
