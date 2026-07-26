"""Acceptance gates for mismatch-calibrated SAR ADC validation.

The project keeps two static questions separate:

1. Does a slow-ramp code-density measurement have no missing codes and bounded
   DNL/INL?
2. Is the actual decoded transfer order-preserving at every reachable decision
   boundary under capacitor mismatch?

The first question cannot prove the second for a redundant SAR because several
disjoint input intervals can accumulate into the same histogram bin.  The
project therefore reports both verdicts.  Strict monotonicity is not silently
promoted into the existing performance acceptance contract; an application
that requires it must enable that requirement explicitly.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def evaluate_acceptance(
    *,
    n_valid: int,
    n_seeds: int,
    calibrated_enob: Sequence[float],
    calibrated_sndr_db: Sequence[float],
    min_enob_bits: float,
    min_sndr_db: float,
    total_missing_codes: int,
    max_integer_jumps: Sequence[int],
    dnl_peaks_lsb: Sequence[float],
    inl_peaks_lsb: Sequence[float],
    total_integer_backsteps: int,
    require_strict_monotonicity: bool = False,
) -> dict[str, str]:
    """Return independent dynamic, histogram, and transfer-integrity verdicts."""

    enob = np.asarray(calibrated_enob, dtype=float)
    sndr = np.asarray(calibrated_sndr_db, dtype=float)
    jumps = np.asarray(max_integer_jumps, dtype=int)
    dnl = np.asarray(dnl_peaks_lsb, dtype=float)
    inl = np.asarray(inl_peaks_lsb, dtype=float)

    dynamic_pass = (
        n_valid == n_seeds
        and len(enob) == n_seeds
        and len(sndr) == n_seeds
        and bool(np.all(enob > min_enob_bits))
        and bool(np.all(sndr > min_sndr_db))
    )
    code_density_pass = (
        n_valid == n_seeds
        and total_missing_codes == 0
        and len(jumps) == n_seeds
        and bool(np.all(jumps <= 1))
        and len(dnl) == n_seeds
        and bool(np.all(dnl <= 1.0))
        and len(inl) == n_seeds
        and bool(np.all(inl <= 1.0))
    )
    transfer_integrity_pass = (
        n_valid == n_seeds
        and total_integer_backsteps == 0
    )
    overall_pass = dynamic_pass and code_density_pass
    if require_strict_monotonicity:
        overall_pass = overall_pass and transfer_integrity_pass
    return {
        "absolute_dynamic_verdict": "PASS" if dynamic_pass else "FAIL",
        "code_density_static_verdict": (
            "PASS" if code_density_pass else "FAIL"
        ),
        "mismatch_transfer_integrity_verdict": (
            "PASS" if transfer_integrity_pass else "FAIL"
        ),
        "strict_monotonicity_required": (
            "YES" if require_strict_monotonicity else "NO"
        ),
        "acceptance_verdict": "PASS" if overall_pass else "FAIL",
    }
